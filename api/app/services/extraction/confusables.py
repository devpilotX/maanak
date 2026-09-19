"""Glyph pairs a reader confuses, and where that matters.

A reader does not fail loudly on an ambiguous glyph. It returns a plausible character and
a high confidence, and the value looks right until somebody reads it closely. Measured on
the accuracy benchmark, the reader returned "lodised Salt" for "Iodised Salt" in all eight
conditions, at 95 per cent mean confidence, and no profile or dictionary setting fixed it:
capital I and lowercase l are the same shape in most sans-serif faces.

Correcting it silently is the wrong answer here. A rule turning a word-initial lowercase l
into a capital I would also turn "Lemon" into "Iemon" and "Litre" into "Iitre", and this
project keeps what the machine read rather than overwriting it. So the ambiguity is
reported instead: the officer is told which characters could have been misread and why, and
the reading itself is left alone for them to confirm or correct.

The pairs below are the ones that actually occur on printed packaging. Each is a pair of
glyphs that are near-identical in a common face, not merely similar.
"""

from __future__ import annotations

import re

#: Each entry is (what the reader probably returned, what it may really be, why).
CONFUSABLE_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("l", "I", "lowercase L and capital i are the same shape in most sans-serif faces"),
    ("I", "l", "capital i and lowercase L are the same shape in most sans-serif faces"),
    ("0", "O", "zero and capital o differ only by a slash the face may not draw"),
    ("O", "0", "capital o and zero differ only by a slash the face may not draw"),
    ("1", "l", "the digit one and lowercase L are the same shape in several faces"),
    ("5", "S", "a worn five and a capital s are easily exchanged"),
    ("8", "B", "a worn eight and a capital b are easily exchanged"),
    ("rn", "m", "an r beside an n reads as a single m at small sizes"),
)

#: A word that begins with a lowercase letter where the rest of the value is capitalised
#: is the pattern that caught "lodised". Applied to alphabetic tokens of three or more
#: characters, so it does not fire on a unit or an initial.
_TOKEN = re.compile(r"[A-Za-z]{3,}")


def suspect_tokens(value: str) -> list[tuple[str, str]]:
    """Tokens whose first character is a likely misread, with the reason.

    Only the first character is examined. A confusable in the middle of a word is usually
    resolved by the reader's own language model; a confusable at the start is not, because
    there is no preceding context to constrain it.
    """
    found: list[tuple[str, str]] = []
    for token in _TOKEN.findall(value or ""):
        rest = token[1:]
        # The signal is a leading lowercase letter followed by lowercase letters, inside a
        # value whose other words are capitalised. "lodised Salt" matches; "salt" does not.
        if not token[0].islower() or not rest.islower():
            continue
        for wrong, right, reason in CONFUSABLE_PAIRS:
            if len(wrong) == 1 and token[0] == wrong and right.isupper():
                found.append((token, f"{token[0]!r} may be {right!r}: {reason}"))
                break
    return found


def ambiguity_note(value: str) -> str | None:
    """A sentence for the officer, or None when nothing looks ambiguous."""
    if not value:
        return None
    capitalised = [t for t in _TOKEN.findall(value) if t[0].isupper()]
    suspects = suspect_tokens(value)
    # Without at least one capitalised word there is no contrast to judge against, so a
    # value that is entirely lowercase is left alone.
    if not suspects or not capitalised:
        return None
    parts = [f"{token} ({why})" for token, why in suspects]
    return (
        "Check these characters against the photograph before confirming: " + "; ".join(parts) + "."
    )
