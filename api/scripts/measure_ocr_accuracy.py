"""Measure what the reader actually gets right, against known ground truth.

There has never been an accuracy figure for this project, and docs/KNOWN_LIMITS.md says
so, because a real benchmark needs a labelled corpus of photographs that nobody had. This
is not that corpus and does not pretend to be. It is the next best thing that can be
checked: the label generator knows exactly what it drew, so every declaration on the panel
has a known correct value, and the pipeline's output can be compared against it field by
field.

What this measures: whether extraction finds and normalises each declaration correctly
from an image the pipeline has not been tuned against, at several sizes and with several
kinds of degradation. What it does not measure: performance on photographs of real
packaging, which is a different and harder question.

    docker compose run --rm --no-deps -v "$PWD/api:/app" -e API_URL=http://api:8000 \
      --entrypoint python api scripts/measure_ocr_accuracy.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_client import RefreshingClient
from verify_matters import make_label

API = os.environ.get("API_URL", "http://api:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD", "Ganga-Yamuna-2026")

#: What make_label() draws, and therefore the correct answer for each declaration. The
#: generator is the authority here: these strings are read off the lines it renders.
GROUND_TRUTH: dict[str, str] = {
    "mrp": "24.00",
    "net_quantity": "1",
    "unit_sale_price": "5.00",
    "common_generic_name": "Iodised Salt",
    "manufacturer": "Riverside Foods Private Limited",
    "consumer_care_email": "care@example.org",
    "consumer_care_phone": "1800 300 4567",
    "country_of_origin": "India",
    "batch_number": "RS2026A",
    "date_of_manufacture": "2026-02",
}

CONDITIONS: tuple[tuple[str, Any], ...] = (
    ("as generated, 1700x1100", lambda image: image),
    ("scaled to 1200 wide", lambda image: _scale(image, 1200)),
    ("scaled to 900 wide", lambda image: _scale(image, 900)),
    ("rotated 2 degrees", lambda image: _rotate(image, 2.0)),
    ("rotated 6 degrees", lambda image: _rotate(image, 6.0)),
    ("jpeg quality 55", lambda image: _requantise(image, 55)),
    ("slight blur", lambda image: cv2.GaussianBlur(image, (3, 3), 0)),
    ("on a white backdrop", lambda image: _on_white(image)),
)


def _scale(image: np.ndarray, width: int) -> np.ndarray:
    height = int(image.shape[0] * width / image.shape[1])
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def _rotate(image: np.ndarray, degrees: float) -> np.ndarray:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    return cv2.warpAffine(
        image, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(250, 249, 246)
    )


def _requantise(image: np.ndarray, quality: int) -> np.ndarray:
    encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])[1]
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)


def _on_white(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    canvas = np.full((int(height * 1.8), int(width * 1.8), 3), 255, dtype=np.uint8)
    top = (canvas.shape[0] - height) // 2
    left = (canvas.shape[1] - width) // 2
    canvas[top : top + height, left : left + width] = image
    return canvas


def normalise(value: str) -> str:
    """Compare on content, not on punctuation the renderer may add."""
    text = str(value or "").strip().lower()
    for junk in ("\u20b9", "rs.", "rs", ",", "(", ")"):
        text = text.replace(junk, "")
    return " ".join(text.split())


def matches(declaration: str, expected: str, got: str) -> bool:
    want = normalise(expected)
    have = normalise(got)
    if not have:
        return False
    if declaration == "date_of_manufacture":
        # The extractor returns a precision-tagged date; month and year must agree.
        return "2026" in have and ("02" in have or "feb" in have)
    if declaration in {"mrp", "unit_sale_price", "net_quantity"}:
        return want in have or have in want
    return want in have or have in want


def run_condition(client: RefreshingClient, label: str, image: np.ndarray) -> dict[str, Any]:
    def csrf() -> dict[str, str]:
        token = client.cookies.get("maanak_csrf")
        return {"X-CSRF-Token": token} if token else {}

    made = client.post(
        "/api/v1/inspections",
        json={
            "inspection_date": "2026-09-18",
            "source": "field_inspection",
            "product": {
                "brand": "Benchmark",
                "name": f"Reader accuracy, {label}",
                "commodity_category": "salt",
            },
        },
        headers=csrf(),
    )
    if made.status_code >= 400:
        return {"error": f"create {made.status_code}"}
    inspection_id = made.json()["id"]

    data = bytes(cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 95])[1])
    up = client.post(
        f"/api/v1/inspections/{inspection_id}/evidence",
        data={
            "face": "declaration_panel",
            "quality_override_reason": (
                "Reader accuracy benchmark. The image is generated with known content and "
                "deliberately degraded, so a quality refusal is expected and recorded."
            ),
        },
        files={"file": (f"{label}.jpg", data, "image/jpeg")},
        headers=csrf(),
    )
    if up.status_code >= 400:
        return {"error": f"upload {up.status_code}", "body": up.text[:160]}

    job = up.json().get("job_id")
    for _ in range(90):
        time.sleep(2)
        if client.get(f"/api/v1/jobs/{job}").json().get("state") in {
            "succeeded",
            "failed",
            "cancelled",
        }:
            break

    detail = client.get(f"/api/v1/inspections/{inspection_id}").json()
    found: dict[str, str] = {}
    for candidate in detail.get("candidates", []):
        kind = candidate["declaration_type"]
        if candidate.get("machine_state") != "located":
            continue
        shown = candidate.get("display_value") or (candidate.get("normalised_value") or {}).get(
            "display"
        )
        if shown and kind not in found:
            found[kind] = str(shown)

    correct = 0
    wrong: list[str] = []
    missing: list[str] = []
    for declaration, expected in GROUND_TRUTH.items():
        got = found.get(declaration)
        if got is None:
            missing.append(declaration)
        elif matches(declaration, expected, got):
            correct += 1
        else:
            wrong.append(f"{declaration}: wanted {expected!r}, got {got!r}")

    return {
        "correct": correct,
        "total": len(GROUND_TRUTH),
        "wrong": wrong,
        "missing": missing,
        "reference": detail.get("reference"),
    }


def main() -> int:
    base = cv2.imdecode(np.frombuffer(make_label(), np.uint8), cv2.IMREAD_COLOR)
    print(
        f"ground truth: {len(GROUND_TRUTH)} declarations on a {base.shape[1]}x{base.shape[0]} panel"
    )
    print()

    totals = {"correct": 0, "total": 0}
    rows: list[tuple[str, str]] = []
    with RefreshingClient(base_url=API, timeout=240) as client:
        signed = client.post(
            "/api/v1/auth/sign-in",
            json={"email": "inspector@example.org", "password": PASSWORD},
        )
        if signed.status_code != 200:
            print(f"  FAIL  could not sign in: {signed.text[:160]}")
            return 1

        for label, transform in CONDITIONS:
            result = run_condition(client, label, transform(base.copy()))
            if "error" in result:
                print(f"  FAIL  {label}: {result['error']} {result.get('body', '')}")
                rows.append((label, "did not run"))
                continue
            correct = result["correct"]
            total = result["total"]
            totals["correct"] += correct
            totals["total"] += total
            share = correct / total * 100
            print(f"  {label:26} {correct}/{total} fields correct  ({share:.0f}%)")
            for item in result["wrong"]:
                print(f"       wrong   {item}")
            for item in result["missing"]:
                print(f"       missing {item}")
            rows.append((label, f"{correct}/{total}"))

    print()
    share = totals["correct"] / max(totals["total"], 1) * 100
    print(
        f"overall: {totals['correct']}/{totals['total']} declarations read correctly ({share:.1f}%)"
    )
    print()
    print("This is a figure for generated labels under known degradation. It is not an")
    print("accuracy figure for photographs of real packaging, and must not be quoted as one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
