"""Unit tests for profile escalation in read_with_best_profile.

The behaviour under test is a decision, not a calculation: whether a second page-segmentation
mode is attempted at all. So these drive `read_with_best_profile` with a stubbed `run_ocr` and
assert on which profiles it asked for, which is the only way to see the decision without
depending on what Tesseract happens to return for a given picture.

`tests/test_totp.py` checks an algorithm against published vectors. This checks a policy.
"""

from __future__ import annotations

import pytest
from PIL import Image

from app.services import ocr


def _outcome(profile: str, words: int) -> ocr.OcrOutcome:
    """An OcrOutcome with a given number of meaningful words and nothing else real."""
    made = [
        ocr.Word(
            text=f"word{index}",
            confidence=0.9,
            box=[index, 0, index + 5, 10],
            line_index=0,
            block_index=0,
            height_px=10.0,
            script="latin",
        )
        for index in range(words)
    ]
    return ocr.OcrOutcome(
        profile=profile,
        languages="eng",
        engine="tesseract",
        engine_version="5.3.0",
        raw_text=" ".join(word.text for word in made),
        words=made,
        lines=[],
        mean_confidence=0.9 if made else None,
        duration_ms=1,
    )


@pytest.fixture
def blank() -> Image.Image:
    return Image.new("RGB", (40, 20), (255, 255, 255))


def _record(monkeypatch, word_counts: dict[str, int]) -> list[str]:
    """Stub run_ocr and return the list it appends each requested profile to."""
    asked: list[str] = []

    def fake_run_ocr(_image, *, profile_name="default", **_kwargs):
        asked.append(profile_name)
        return _outcome(profile_name, word_counts.get(profile_name, 0))

    monkeypatch.setattr(ocr, "run_ocr", fake_run_ocr)
    return asked


class TestEscalation:
    def test_a_thin_read_escalates_to_sparse(self, monkeypatch, blank) -> None:
        """This is the test that fails without the change: sparse was never requested."""
        asked = _record(monkeypatch, {"default": 3, "english": 4, "sparse": 40})
        ocr.read_with_best_profile(blank)
        assert "sparse" in asked, f"sparse was never attempted; asked for {asked}"

    def test_a_healthy_read_does_not_escalate(self, monkeypatch, blank) -> None:
        """A clean panel must cost exactly two reads, or every inspection slows down."""
        asked = _record(monkeypatch, {"default": 55, "english": 50})
        ocr.read_with_best_profile(blank)
        assert asked == ["default", "english"]
        assert "sparse" not in asked

    def test_the_threshold_is_the_boundary(self, monkeypatch, blank) -> None:
        asked = _record(monkeypatch, {"default": 25, "english": 0})
        ocr.read_with_best_profile(blank, escalate_below_words=25)
        assert "sparse" not in asked, "25 words is not below a threshold of 25"

        asked = _record(monkeypatch, {"default": 24, "english": 0})
        ocr.read_with_best_profile(blank, escalate_below_words=25)
        assert "sparse" in asked, "24 words is below a threshold of 25"

    def test_the_better_read_still_wins(self, monkeypatch, blank) -> None:
        """Escalation adds a candidate; it does not force the result."""
        _record(monkeypatch, {"default": 2, "english": 2, "sparse": 40})
        assert ocr.read_with_best_profile(blank).profile == "sparse"

        _record(monkeypatch, {"default": 20, "english": 2, "sparse": 1})
        assert ocr.read_with_best_profile(blank).profile == "default"

    def test_escalation_is_recorded_in_the_warnings(self, monkeypatch, blank) -> None:
        """A decision the pipeline made for the officer has to be visible."""
        _record(monkeypatch, {"default": 2, "english": 2, "sparse": 40})
        outcome = ocr.read_with_best_profile(blank)
        joined = " ".join(outcome.warnings)
        assert "sparse" in joined
        assert "tried as well" in joined

    def test_a_profile_already_requested_is_not_repeated(self, monkeypatch, blank) -> None:
        asked = _record(monkeypatch, {"default": 1, "sparse": 2})
        ocr.read_with_best_profile(blank, profile_names=("default", "sparse"))
        assert asked.count("sparse") == 1

    def test_escalation_can_be_turned_off(self, monkeypatch, blank) -> None:
        asked = _record(monkeypatch, {"default": 1, "english": 1})
        ocr.read_with_best_profile(blank, escalate_to=())
        assert asked == ["default", "english"]

    def test_an_unknown_escalation_profile_is_ignored(self, monkeypatch, blank) -> None:
        asked = _record(monkeypatch, {"default": 1, "english": 1})
        ocr.read_with_best_profile(blank, escalate_to=("no-such-profile",))
        assert asked == ["default", "english"]

    def test_every_attempt_failing_still_returns_an_outcome(self, monkeypatch, blank) -> None:
        """A page that reads as nothing must not raise; the caller decides what it means."""

        def all_failed(_image, *, profile_name="default", **_kwargs):
            outcome = _outcome(profile_name, 0)
            outcome.failure_reason = "engine refused"
            return outcome

        monkeypatch.setattr(ocr, "run_ocr", all_failed)
        result = ocr.read_with_best_profile(blank)
        assert result.failure_reason == "engine refused"
