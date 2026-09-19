"""Prove a restore produced the same system, rather than assuming it did.

docs/BACKUP_RESTORE.md lists four checks and expects them run by hand against a browser
session. All four can be done against the database directly, which is both stronger and needs
no credentials, because the application already owns the code that does them:

  audit.verify_chain      recomputes every hash and relinks the chain, so an altered field,
                          a removed row and a rewritten link are all detected
  audit.chain_head        head sequence and hash, to compare against what the backup recorded
  evidence.verify_integrity  re-reads each stored object and compares it to the SHA-256 taken
                          at upload, which is the only way to catch object storage that
                          restored short
  reports.verify_snapshot recomputes the frozen snapshot hash

Exits non-zero on any failure, and refuses to pass when it found nothing to check. An empty
database verifies trivially, and this project has been caught by that three times elsewhere.

    docker compose run --rm --no-deps -v "$PWD:/repo" -e PYTHONPATH=/repo/api migrate \
      python /repo/api/scripts/verify_restore.py \
      --expect /repo/backup/<stamp>/audit-chain-at-backup.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text

from app.db import session_scope
from app.models.audit import AuditEvent
from app.models.evidence import Evidence
from app.models.report import Report
from app.services import audit as audit_service
from app.services import evidence as evidence_service
from app.services import storage as storage_service
from app.services.reports import snapshot as snapshot_service

passed = 0
failed: list[str] = []


def check(ok: bool, message: str) -> bool:
    global passed
    if ok:
        passed += 1
        print(f"  ok    {message}")
    else:
        failed.append(message)
        print(f"  FAIL  {message}")
    return ok


async def run(expected: dict[str, Any] | None) -> None:
    async with session_scope() as db:
        print("the audit chain")
        head = await audit_service.chain_summary(db)
        events = int(head.get("event_count") or 0)
        check(events > 0, f"the restored trail holds events ({events})")

        verification = await audit_service.verify_chain(db)
        check(
            verification.intact,
            f"every hash recomputes and every link holds ({verification.events_checked} events)"
            + ("" if verification.intact else f": {verification.problem}"),
        )

        if expected:
            want_seq = int(expected.get("head_sequence") or 0)
            want_hash = (expected.get("head_hash") or "").strip()
            want_count = int(expected.get("event_count") or 0)
            got_seq = int(head.get("head_sequence") or 0)
            got_hash = (head.get("head_hash") or "").strip()
            check(
                got_seq == want_seq,
                f"head sequence matches the backup ({got_seq} against {want_seq})",
            )
            check(
                got_hash == want_hash,
                f"head hash matches the backup ({got_hash[:16]} against {want_hash[:16]})",
            )
            check(
                events == want_count,
                f"event count matches the backup ({events} against {want_count})",
            )
        else:
            print("      no --expect given, so the trail is checked but not compared")

    print("append-only protection")
    # A restore that lost the triggers would pass a row count and fail here. The update is
    # expected to raise; succeeding is the failure. Its own session, because the rollback
    # would otherwise poison the checks that follow.
    async with session_scope() as db:
        try:
            await db.execute(
                AuditEvent.__table__.update()
                .where(AuditEvent.sequence == 1)
                .values(reason="tampered by verify_restore")
            )
            await db.flush()
            check(False, "audit_events still refuses UPDATE, but the update succeeded")
        except Exception as error:
            message = str(error).lower()
            check(
                "42501" in message or "immutable" in message or "append" in message,
                f"audit_events still refuses UPDATE ({type(error).__name__})",
            )

    async with session_scope() as db:
        print("evidence bytes against the hash recorded at upload")
        rows = (await db.execute(select(Evidence))).scalars().all()
        check(len(rows) > 0, f"the restore holds evidence to check ({len(rows)})")
        bad = []
        for item in rows:
            try:
                outcome = await evidence_service.verify_integrity(db, item)
            except Exception as error:
                bad.append(f"{item.id}: {type(error).__name__}")
                continue
            if not outcome.get("verified"):
                bad.append(f"{item.id}: {outcome.get('reason') or 'hash mismatch'}")
        check(not bad, f"every evidence object matches its hash ({len(rows)} checked)")
        for entry in bad[:5]:
            print(f"        {entry}")

    # Evidence is not the only thing in object storage. Corrupting a complaint attachment
    # went undetected until these were added, because only the evidence table was read.
    # Every table carrying a storage key and a sha256 is now swept. storage.verify_stored_hash
    # exists for exactly this and its own docstring names the backup-restore check.
    async with session_scope() as db:
        print("every other stored object against its recorded hash")
        total = 0
        wrong: list[str] = []
        for table, label, logical in (
            ("complaint_attachments", "complaint attachment", storage_service.Bucket.ORIGINALS),
            ("evidence_derivatives", "derivative", storage_service.Bucket.DERIVATIVES),
            ("report_documents", "report document", storage_service.Bucket.REPORTS),
        ):
            result = await db.execute(
                text(f"select id, storage_key, sha256 from {table}")  # noqa: S608 - fixed names
            )
            for row in result.mappings():
                total += 1
                try:
                    matches = await storage_service.verify_stored_hash(
                        logical_bucket=logical,
                        key=row["storage_key"],
                        expected_sha256=row["sha256"] or "",
                    )
                except Exception as error:
                    wrong.append(f"{label} {row['id']}: {type(error).__name__}")
                    continue
                if not matches:
                    wrong.append(f"{label} {row['id']}: hash mismatch")
        check(total > 0, f"the restore holds other objects to check ({total})")
        check(not wrong, f"every other object matches its hash ({total} checked)")
        for entry in wrong[:5]:
            print(f"        {entry}")

    async with session_scope() as db:
        print("report snapshots")
        reports = (await db.execute(select(Report))).scalars().all()
        if not reports:
            print("      no reports in this restore, nothing to recompute")
        else:
            broken = []
            for report in reports:
                try:
                    outcome = snapshot_service.verify_snapshot(report)
                except Exception as error:
                    broken.append(f"{report.reference}: {type(error).__name__}")
                    continue
                if not outcome.get("intact"):
                    broken.append(f"{report.reference}: snapshot hash mismatch")
            check(not broken, f"every report snapshot recomputes ({len(reports)} checked)")
            for entry in broken[:5]:
                print(f"        {entry}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expect",
        help="audit-chain-at-backup.json written by scripts/backup.sh",
    )
    options = parser.parse_args()

    expected = None
    if options.expect:
        path = Path(options.expect)
        if not path.exists():
            print(f"FAIL  no such file: {path}")
            return 2
        expected = json.loads(path.read_text(encoding="utf-8"))
        print(
            f"comparing against {path.name}: sequence {expected.get('head_sequence')}, "
            f"{expected.get('event_count')} events"
        )
        print()

    asyncio.run(run(expected))

    print()
    print(f"checks passed: {passed}")
    print(f"checks failed: {len(failed)}")
    if failed:
        for item in failed:
            print(f"  - {item}")
        print()
        print("This restore is not trustworthy. Investigate rather than proceed.")
        return 1
    if passed == 0:
        print("nothing was checked, which is not the same as a clean restore.")
        return 2
    print()
    print("the restore holds the same trail, the same evidence and the same reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
