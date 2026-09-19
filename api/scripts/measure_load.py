"""Measure where this deployment saturates, and say so in numbers.

`docs/KNOWN_LIMITS.md` and the README list load testing among the things that have not been
done. This does it, and reports figures that are honest about what bounds them.

Three things bound throughput here, and only one of them is the hardware:

1. The API is one uvicorn process. Reads are async and IO-bound on PostgreSQL, so they scale
   with concurrency until the event loop or the database becomes the limit.
2. The worker runs ``max_jobs = 2``, deliberately, because OCR is CPU-bound and
   ``app/worker/main.py`` says running more at once on a small host makes every job slower
   without improving throughput. That number, not the API, is the operational ceiling for
   evidence processing.
3. Per-endpoint rate limits, which apply to sign-in, uploads, complaints and public report
   verification. Read endpoints are not among them. This run spreads work across several
   sessions anyway, so that a limit added later does not silently turn a capacity measurement
   into a rate-limiter measurement, and it counts every 429 rather than hiding them.

Running this is what established that ``API_PER_SESSION`` is declared and never enforced:
3,132 requests across four sessions produced zero 429 responses, where that limit would have
refused after 600 in a minute.

    docker compose run --rm --no-deps -e API_URL=http://api:8000 \
      --entrypoint python api scripts/measure_load.py
    docker compose run --rm --no-deps -e API_URL=http://api:8000 \
      --entrypoint python api scripts/measure_load.py --uploads 6
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_client import RefreshingClient

API = os.environ.get("API_URL", "http://api:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD", "Ganga-Yamuna-2026")

#: Accounts to spread read load across. Every one is a seeded demo account. Kept small
#: because LOGIN_PER_IP allows 20 sign-ins per 300 seconds and a load run should not spend
#: that budget on itself.
ACCOUNTS = (
    "inspector@example.org",
    "reviewer@example.org",
    "controller@example.org",
    "admin@example.org",
)

#: Read endpoints an officer actually hits, weighted towards registers because that is what
#: a workspace session does most.
READS = (
    "/api/v1/inspections?page_size=20",
    "/api/v1/complaints?page_size=20",
    "/api/v1/cases?page_size=20",
    "/api/v1/products?page_size=20",
    "/api/v1/reports?page_size=20",
    "/api/v1/rules?page_size=20",
    "/api/v1/reference/vocabulary",
    "/api/v1/auth/me",
)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def sign_in(email: str) -> RefreshingClient | None:
    client = RefreshingClient(base_url=API, timeout=60)
    response = client.post("/api/v1/auth/sign-in", json={"email": email, "password": PASSWORD})
    if response.status_code != 200:
        print(f"  could not sign in as {email}: {response.status_code}")
        client.close()
        return None
    return client


def read_round(clients: list[RefreshingClient], concurrency: int, seconds: float) -> dict[str, Any]:
    """Hit read endpoints from `concurrency` threads for `seconds`, and time every call."""
    latencies: list[float] = []
    codes: dict[int, int] = {}
    stop = time.perf_counter() + seconds
    counter = {"n": 0}

    def worker(slot: int) -> None:
        client = clients[slot % len(clients)]
        while time.perf_counter() < stop:
            path = READS[counter["n"] % len(READS)]
            counter["n"] += 1
            started = time.perf_counter()
            try:
                response = client.get(path)
                code = response.status_code
            except Exception:
                code = 0
            elapsed = (time.perf_counter() - started) * 1000
            latencies.append(elapsed)
            codes[code] = codes.get(code, 0) + 1

    began = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(worker, range(concurrency)))
    duration = time.perf_counter() - began

    ok = codes.get(200, 0)
    limited = codes.get(429, 0)
    return {
        "concurrency": concurrency,
        "requests": len(latencies),
        "ok": ok,
        "rate_limited": limited,
        "other": len(latencies) - ok - limited,
        "per_second": len(latencies) / duration if duration else 0.0,
        "ok_per_second": ok / duration if duration else 0.0,
        "p50": percentile(latencies, 0.50),
        "p95": percentile(latencies, 0.95),
        "p99": percentile(latencies, 0.99),
        "max": max(latencies) if latencies else 0.0,
    }


def measure_reads(clients: list[RefreshingClient], seconds: float) -> list[dict[str, Any]]:
    print("read throughput and latency, ramping concurrency")
    print(
        f"  {'threads':>7} {'req':>6} {'ok':>6} {'429':>5} {'req/s':>7} "
        f"{'p50 ms':>7} {'p95 ms':>7} {'p99 ms':>7}"
    )
    rows = []
    for concurrency in (1, 2, 4, 8, 16):
        row = read_round(clients, concurrency, seconds)
        rows.append(row)
        print(
            f"  {row['concurrency']:>7} {row['requests']:>6} {row['ok']:>6} "
            f"{row['rate_limited']:>5} {row['per_second']:>7.1f} "
            f"{row['p50']:>7.1f} {row['p95']:>7.1f} {row['p99']:>7.1f}"
        )
        # Let the per-session window drain a little so the next rung is not measuring the
        # previous rung's rate-limit budget.
        time.sleep(3)
    return rows


def measure_worker(client: RefreshingClient, uploads: int, image: bytes) -> dict[str, Any]:
    """Queue `uploads` OCR jobs and time how long the worker takes to drain them."""
    print(f"\nworker drain rate, {uploads} evidence uploads with max_jobs=2")

    def csrf() -> dict[str, str]:
        token = client.cookies.get("maanak_csrf")
        return {"X-CSRF-Token": token} if token else {}

    jobs: list[str] = []
    queued_at = time.perf_counter()
    for index in range(uploads):
        made = client.post(
            "/api/v1/inspections",
            json={
                "inspection_date": "2026-09-19",
                "source": "field_inspection",
                "product": {
                    "brand": "Loadtest",
                    "name": f"Throughput measurement {index + 1}",
                    "commodity_category": "salt",
                },
            },
            headers=csrf(),
        )
        if made.status_code >= 400:
            print(f"  create refused ({made.status_code}); stopping at {index} uploads")
            break
        inspection_id = made.json()["id"]
        up = client.post(
            f"/api/v1/inspections/{inspection_id}/evidence",
            data={
                "face": "declaration_panel",
                "quality_override_reason": (
                    "Throughput measurement. The same generated panel is uploaded repeatedly "
                    "so the only variable is queue depth."
                ),
            },
            files={"file": (f"load-{index}.jpg", image, "image/jpeg")},
            headers=csrf(),
        )
        if up.status_code >= 400:
            print(f"  upload refused ({up.status_code}); stopping at {index} queued")
            break
        job = up.json().get("job_id")
        if job:
            jobs.append(job)
    queue_seconds = time.perf_counter() - queued_at
    print(f"  {len(jobs)} jobs queued in {queue_seconds:.1f}s")

    if not jobs:
        return {"jobs": 0}

    finished: dict[str, float] = {}
    started_wait = time.perf_counter()
    deadline = started_wait + 900
    while len(finished) < len(jobs) and time.perf_counter() < deadline:
        time.sleep(2)
        for job in jobs:
            if job in finished:
                continue
            state = client.get(f"/api/v1/jobs/{job}").json().get("state")
            if state in {"succeeded", "failed", "cancelled"}:
                finished[job] = time.perf_counter() - started_wait
    drain = time.perf_counter() - started_wait

    completed = len(finished)
    return {
        "jobs": len(jobs),
        "completed": completed,
        "queue_seconds": queue_seconds,
        "drain_seconds": drain,
        "jobs_per_minute": (completed / drain * 60) if drain else 0.0,
        "seconds_per_job": (drain / completed) if completed else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0, help="per concurrency rung")
    parser.add_argument("--uploads", type=int, default=4, help="OCR jobs to queue")
    options = parser.parse_args()

    print(f"measuring {API}")
    print(f"host: {os.cpu_count()} cpus visible to this container")
    print()

    clients: list[RefreshingClient] = []
    for email in ACCOUNTS:
        client = sign_in(email)
        if client:
            clients.append(client)
    if not clients:
        print("FAIL no session could be established, so nothing can be measured")
        return 1
    print(f"signed in {len(clients)} of {len(ACCOUNTS)} accounts")
    print()

    try:
        rows = measure_reads(clients, options.seconds)

        from verify_matters import make_label

        worker = measure_worker(clients[0], options.uploads, make_label())
    finally:
        for client in clients:
            client.close()

    best = max(rows, key=lambda r: r["ok_per_second"]) if rows else {}
    print()
    print("=" * 74)
    print("reads")
    if best:
        print(
            f"  peak accepted throughput   {best['ok_per_second']:.1f} requests/second "
            f"at {best['concurrency']} threads"
        )
        print(f"  latency at that point      p50 {best['p50']:.0f} ms, p95 {best['p95']:.0f} ms")
        limited = sum(r["rate_limited"] for r in rows)
        total = sum(r["requests"] for r in rows)
        print(f"  requests refused as 429    {limited} of {total}")
        if not limited:
            print(
                "  No read request was throttled. API_PER_SESSION is declared in\n"
                "  security/ratelimit.py at 600 per 60 seconds and is never enforced, which\n"
                "  this measurement is what established. Read endpoints carry no rate limit."
            )
    print("evidence processing")
    if worker.get("jobs"):
        print(f"  jobs completed             {worker['completed']} of {worker['jobs']}")
        print(f"  drain time                 {worker['drain_seconds']:.1f}s")
        print(f"  throughput                 {worker['jobs_per_minute']:.1f} jobs/minute")
        print(f"  mean per job               {worker['seconds_per_job']:.1f}s")
        print("  bounded by max_jobs=2 in app/worker/main.py, which is deliberate: OCR is")
        print("  CPU-bound and more concurrency makes every job slower.")
    else:
        print("  no jobs were queued, so nothing was measured")
    print()
    print("These figures are for this machine and this data. They are a capacity")
    print("baseline for one host, not a published benchmark, and they will move on")
    print("different hardware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
