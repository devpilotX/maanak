"""Measure the reader against photographs of real packaging, not generated labels.

``measure_ocr_accuracy.py`` scores the pipeline on a label this project draws itself. That
figure is useful and it is also the easy case: the panel is flat, evenly lit, printed in
one clean face and photographed by nothing at all. It says so in its own output, and
``docs/KNOWN_LIMITS.md`` records that no figure existed for real packaging.

This is that harder measurement. The photographs are ordinary contributions to Open Food
Facts: real Indian packs, held by hand, under kitchen and shop lighting, creased, curved,
reflective, sometimes half in shadow. The database records each product's brand, name and
declared net quantity, and that declared quantity is the ground truth compared against
here.

Two things are measured, and the second matters more than the first.

1. What the reader extracts from a real photograph, and whether the net quantity it reads
   agrees with the quantity the database records.
2. Whether a photograph that does not show a declaration ever produces a non-compliant
   finding. It must not. That is the first rule in the README, and real photographs are a
   far better test of it than a synthetic panel, because most real photographs genuinely
   do fail to show most of the panel.

Expect a low extraction rate and read it as the honest number rather than a disappointing
one. A consumer photograph of the front of a biscuit packet does not show the consumer
care address, so not finding one is correct behaviour.

    python scripts/measure_ocr_real.py --manifest /labels/manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_client import RefreshingClient

API = os.environ.get("API_URL", "http://api:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD", "Ganga-Yamuna-2026")

#: Enough of a reason to satisfy the override, and truthful about why it is used.
OVERRIDE = (
    "Reader benchmark against real packaging photographs contributed by the public. The "
    "quality signals are expected to be poor, and measuring what the reader does with a "
    "poor photograph is the purpose of the run."
)

QUANTITY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|gm|gms|gram|grams|ml|l|litre|litres|kilogram)\b")

#: Units that mean the same thing, so "45gm" and "45 g" agree.
SAME: dict[str, str] = {
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "litre": "l",
    "litres": "l",
}


def canonical(text: str) -> tuple[str, str] | None:
    """(amount, unit) from a free-text quantity, or None when there is no unit."""
    found = QUANTITY.search((text or "").lower().replace(",", ""))
    if not found:
        return None
    amount, unit = found.group(1), found.group(2)
    unit = SAME.get(unit, unit)
    # Compare on a single scale so 1 kg and 1000 g agree.
    if unit == "kg":
        amount, unit = str(float(amount) * 1000), "g"
    if unit == "l":
        amount, unit = str(float(amount) * 1000), "ml"
    return (str(float(amount)), unit)


def csrf_headers(client: RefreshingClient) -> dict[str, str]:
    token = client.cookies.get("maanak_csrf")
    return {"X-CSRF-Token": token} if token else {}


def one_photograph(client: RefreshingClient, item: dict[str, Any], folder: Path) -> dict[str, Any]:
    truth = item["truth"]
    result: dict[str, Any] = {"code": item["code"], "truth": truth}

    made = client.post(
        "/api/v1/inspections",
        json={
            "inspection_date": "2026-09-19",
            "source": "field_inspection",
            "product": {
                "brand": (truth.get("brands") or "unrecorded")[:120],
                "name": (truth.get("product_name") or "unrecorded")[:200],
                "commodity_category": "other",
            },
        },
        headers=csrf_headers(client),
    )
    if made.status_code >= 400:
        result["error"] = f"create {made.status_code}: {made.text[:120]}"
        return result
    inspection_id = made.json()["id"]
    result["inspection"] = made.json().get("reference")

    # The manifest records the path it was written at, which is not where the file is
    # mounted inside the container. Only the name is used, resolved beside the manifest.
    name = Path(item["file"]).name
    source = folder / "img" / name
    if not source.exists():
        source = folder / name
    data = source.read_bytes()

    # First without an override, to record whether the quality gate would refuse a real
    # consumer photograph and what it would tell the officer to fix.
    plain = client.post(
        f"/api/v1/inspections/{inspection_id}/evidence",
        data={"face": "declaration_panel"},
        files={"file": (name, data, "image/jpeg")},
        headers=csrf_headers(client),
    )
    result["gate_refused"] = plain.status_code >= 400
    if result["gate_refused"]:
        try:
            body = plain.json()
            result["gate_reason"] = str(
                body.get("detail") or body.get("message") or body.get("error") or ""
            )[:300]
        except Exception:  # the reason is a nicety, not the measurement
            result["gate_reason"] = plain.text[:300]
        sent = client.post(
            f"/api/v1/inspections/{inspection_id}/evidence",
            data={"face": "declaration_panel", "quality_override_reason": OVERRIDE},
            files={"file": (name, data, "image/jpeg")},
            headers=csrf_headers(client),
        )
    else:
        sent = plain
    if sent.status_code >= 400:
        result["error"] = f"upload {sent.status_code}: {sent.text[:160]}"
        return result

    job = sent.json().get("job_id")
    for _ in range(120):
        time.sleep(2)
        state = client.get(f"/api/v1/jobs/{job}").json().get("state")
        if state in {"succeeded", "failed", "cancelled"}:
            result["job_state"] = state
            break

    detail = client.get(f"/api/v1/inspections/{inspection_id}").json()
    located: dict[str, str] = {}
    for candidate in detail.get("candidates", []):
        if candidate.get("machine_state") != "located":
            continue
        kind = candidate["declaration_type"]
        shown = candidate.get("display_value") or (candidate.get("normalised_value") or {}).get(
            "display"
        )
        if shown and kind not in located:
            located[kind] = str(shown)
    result["located"] = located

    # Net quantity is the one declaration with independent ground truth.
    want = canonical(truth.get("quantity", ""))
    got = canonical(located.get("net_quantity", ""))
    result["quantity_truth"] = want
    result["quantity_read"] = got
    result["quantity_verdict"] = (
        "no ground truth"
        if want is None
        else "not read"
        if got is None
        else "agrees"
        if want == got
        else "disagrees"
    )

    # The invariant. Checks run before any officer review, so nothing is reviewed and
    # nothing may be reported as non-compliant.
    checks = client.post(
        f"/api/v1/inspections/{inspection_id}/checks", headers=csrf_headers(client)
    )
    if checks.status_code == 200:
        result["outcomes"] = checks.json().get("outcomes", {})
    else:
        result["outcomes"] = {"error": checks.status_code}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    options = parser.parse_args()

    items = json.loads(Path(options.manifest).read_text(encoding="utf-8"))
    folder = Path(options.manifest).resolve().parent
    print(f"{len(items)} photographs of real packaging, ground truth from Open Food Facts")
    print()

    rows: list[dict[str, Any]] = []
    with RefreshingClient(base_url=API, timeout=300) as client:
        signed = client.post(
            "/api/v1/auth/sign-in",
            json={"email": "inspector@example.org", "password": PASSWORD},
        )
        if signed.status_code != 200:
            print(f"FAIL could not sign in: {signed.text[:160]}")
            return 1

        for item in items:
            row = one_photograph(client, item, folder)
            rows.append(row)
            truth = row["truth"]
            head = f"{row['code']}  {truth['product_name'][:26]:26}"
            if "error" in row:
                print(f"  FAIL  {head} {row['error']}")
                continue
            gate = "refused" if row.get("gate_refused") else "accepted"
            print(
                f"  {head} gate={gate:8} declarations={len(row['located']):>2}  "
                f"net quantity: {row['quantity_verdict']}"
            )
            if row["quantity_verdict"] in {"agrees", "disagrees"}:
                print(
                    f"        declared {truth['quantity']!r} -> read "
                    f"{row['located'].get('net_quantity')!r}"
                )
            if row["located"]:
                print(f"        found: {', '.join(sorted(row['located']))}")
            bad = row.get("outcomes", {}).get("non_compliant", 0)
            if bad:
                print(f"        NON-COMPLIANT FINDINGS WITHOUT REVIEW: {bad}")

    ran = [r for r in rows if "error" not in r]
    print()
    print("=" * 78)
    print(f"photographs processed          {len(ran)} of {len(rows)}")
    print(f"refused by the quality gate    {sum(1 for r in ran if r.get('gate_refused'))}")
    print(f"accepted without an override   {sum(1 for r in ran if not r.get('gate_refused'))}")
    total_found = sum(len(r["located"]) for r in ran)
    print(f"declarations located in total  {total_found}")
    with_any = sum(1 for r in ran if r["located"])
    print(f"photographs yielding at least one declaration  {with_any} of {len(ran)}")

    print()
    print("net quantity against the declared quantity in the database:")
    verdicts = [r["quantity_verdict"] for r in ran]
    agrees = verdicts.count("agrees")
    disagrees = verdicts.count("disagrees")
    unread = verdicts.count("not read")
    print(f"  agrees      {agrees}")
    print(f"  disagrees   {disagrees}")
    print(f"  not read    {unread}")
    if agrees + disagrees:
        share = agrees / (agrees + disagrees) * 100
        print(f"  of those read, {agrees}/{agrees + disagrees} agree ({share:.0f}%)")

    print()
    offenders = [r for r in ran if r.get("outcomes", {}).get("non_compliant")]
    print("the invariant: absent evidence is never a violation")
    print(f"  photographs producing a non-compliant finding before review: {len(offenders)}")
    for row in offenders:
        print(f"    {row['code']} {row['outcomes']}")

    print()
    print("This measures photographs of real packaging contributed by the public. A low")
    print("extraction rate is the expected and correct result: a photograph of the front")
    print("of a packet does not show the declaration panel, and the system is built to")
    print("say so rather than to guess.")
    return 1 if offenders or not ran else 0


if __name__ == "__main__":
    raise SystemExit(main())
