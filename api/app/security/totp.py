"""Time-based one-time passwords, RFC 6238, from the standard library.

No dependency is added for this. RFC 6238 is HMAC-SHA1 over a counter derived from the
clock, truncated to six digits, and the whole of it is below. Adding a package to do thirty
lines of `hmac` would enlarge the supply chain this project already scans and pins for the
sake of convenience.

Interoperable with Google Authenticator, Aegis, 1Password and FreeOTP: SHA-1, six digits,
thirty-second steps, base32 secret. Those parameters are not chosen, they are what
authenticator applications implement, and a deployment that changed them would find that
half of them silently ignore the change.

Two properties worth naming because they are security-relevant rather than incidental:

* Verification accepts a window of adjacent steps, because a phone clock and a server clock
  are never exactly aligned. The window is small and symmetric. Widening it to be helpful
  multiplies the number of codes valid at any moment.
* Comparison is constant time. A digit-by-digit comparison that returns early leaks how much
  of a guess was right, which is enough to find a code by measurement.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

#: Bytes of entropy in a new secret. RFC 4226 requires at least 128 bits and recommends 160,
#: which is 20 bytes, and is what authenticator applications expect.
SECRET_BYTES = 20

#: Seconds per step. Thirty is what every authenticator application assumes.
STEP_SECONDS = 30

#: Digits in a code.
DIGITS = 6

#: Steps either side of the current one that are accepted. One step is 30 seconds, so this
#: tolerates 30 seconds of clock skew in each direction and no more.
DEFAULT_WINDOW = 1


def generate_secret() -> str:
    """A new base32 secret, unpadded, as authenticator applications expect."""
    raw = secrets.token_bytes(SECRET_BYTES)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    """Base32 with the padding an authenticator application usually omits."""
    cleaned = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(cleaned) % 8) % 8)
    return base64.b32decode(cleaned + padding, casefold=True)


def code_at(secret: str, *, counter: int) -> str:
    """The six-digit code for one counter value."""
    key = _decode_secret(secret)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    # Dynamic truncation, RFC 4226 section 5.3: the low nibble of the last byte selects
    # where in the digest to read the 31-bit integer from.
    offset = digest[-1] & 0x0F
    (chunk,) = struct.unpack(">I", digest[offset : offset + 4])
    return str((chunk & 0x7FFFFFFF) % (10**DIGITS)).zfill(DIGITS)


def current_code(secret: str, *, at: float | None = None) -> str:
    """The code for the current step, for tests and for showing an enrolment worked."""
    moment = time.time() if at is None else at
    return code_at(secret, counter=int(moment // STEP_SECONDS))


def verify(
    secret: str, candidate: str, *, at: float | None = None, window: int = DEFAULT_WINDOW
) -> bool:
    """True when `candidate` matches any accepted step.

    Every comparison runs, and each one is constant time, so neither the answer nor the step
    that matched can be inferred from how long this took.
    """
    if not secret or not candidate:
        return False
    digits = "".join(character for character in candidate if character.isdigit())
    if len(digits) != DIGITS:
        return False
    moment = time.time() if at is None else at
    step = int(moment // STEP_SECONDS)
    matched = False
    for offset in range(-window, window + 1):
        try:
            expected = code_at(secret, counter=step + offset)
        except Exception:  # noqa: BLE001 - a malformed secret is a failure, not a crash
            return False
        # No short circuit: every candidate is compared so the timing does not vary.
        matched |= hmac.compare_digest(expected, digits)
    return matched


def provisioning_uri(*, secret: str, account: str, issuer: str) -> str:
    """An ``otpauth://`` URI an authenticator application can be pointed at.

    The label carries the issuer as well as the account, which is what makes the entry read
    "Maanak: someone@example.org" in the application rather than an unlabelled six digits
    beside five others.
    """
    label = quote(f"{issuer}:{account}", safe="")
    query = urlencode(
        {
            "secret": secret,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": str(DIGITS),
            "period": str(STEP_SECONDS),
        }
    )
    return f"otpauth://totp/{label}?{query}"
