"""Second factor: enrolment, the sign-in challenge, and removal.

Shape of the sign-in flow once a second factor is enrolled:

1. ``POST /auth/sign-in`` verifies the password and, instead of opening a session, returns
   401 with code ``mfa_required`` and a short-lived challenge. No cookies are set, so a
   correct password alone is worth nothing.
2. ``POST /auth/mfa/verify`` takes that challenge and a code and opens the session.

The challenge is a signed token rather than server state, with a five minute life, its own
type claim so it cannot be presented anywhere an access token is accepted, and the session
that will be opened is not created until the code is checked. It carries no role or
jurisdiction, so a stolen challenge grants nothing on its own.

Recovery is deliberately administrator-mediated rather than by recovery codes. Codes have to
be delivered and stored somewhere, and this deployment has no mail service, so printing them
to a browser once and hoping is not a recovery plan. An administrator already holds
``user.reset_password``; resetting a second factor is the same kind of act, is audited the
same way, and leaves a named person accountable for it.
"""

from __future__ import annotations

import base64
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import PermissionDeniedError, ValidationError
from ..models.user import User
from ..security import passwords, totp
from ..security.tokens import ALGORITHM
from ..services import audit as audit_service

#: Type claim on a challenge. Distinct from the access token type so the two can never be
#: mistaken for one another by a decoder that forgets to check.
CHALLENGE_TYPE = "mfa_challenge"

#: A challenge is for finishing a sign-in that is already in progress, not for holding open.
CHALLENGE_TTL_SECONDS = 300

ISSUER_LABEL = "Maanak"


def issue_challenge(user: User) -> str:
    """A signed, short-lived token that says only "this account passed its password"."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "typ": CHALLENGE_TYPE,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=CHALLENGE_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def read_challenge(challenge: str) -> uuid.UUID:
    """The account a challenge refers to, or a refusal.

    Every failure raises the same error with the same message. A client that could tell an
    expired challenge from a forged one would learn something about the signing key.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            challenge,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "typ"]},
        )
    except Exception as error:  # every reason answers identically
        raise PermissionDeniedError(
            "This sign-in attempt is no longer valid. Start again.",
            code="mfa_challenge_invalid",
        ) from error
    if payload.get("typ") != CHALLENGE_TYPE:
        raise PermissionDeniedError(
            "This sign-in attempt is no longer valid. Start again.",
            code="mfa_challenge_invalid",
        )
    return uuid.UUID(str(payload["sub"]))


def qr_png_base64(uri: str) -> str:
    """The provisioning URI as a PNG, base64 encoded for embedding in the page.

    A data URI rather than a stored file: the secret must not be written to object storage,
    and it is only needed for the seconds the officer spends scanning it.
    """
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


async def begin_enrolment(db: AsyncSession, user: User) -> dict[str, str]:
    """Generate a secret and return what an authenticator application needs.

    The secret is stored but ``mfa_enabled`` stays false until a code proves the officer
    actually holds it. Enabling first would lock an account out of its own second factor if
    the scan failed.
    """
    if user.mfa_enabled:
        raise ValidationError(
            "A second factor is already enrolled on this account. Remove it before enrolling "
            "another.",
            code="mfa_already_enrolled",
        )
    secret = totp.generate_secret()
    user.mfa_secret = secret
    await db.flush()
    uri = totp.provisioning_uri(secret=secret, account=user.email, issuer=ISSUER_LABEL)
    return {"secret": secret, "provisioning_uri": uri, "qr_png_base64": qr_png_base64(uri)}


async def confirm_enrolment(
    db: AsyncSession, context: audit_service.AuditContext, user: User, code: str
) -> None:
    """Enable the second factor once a code from the authenticator verifies."""
    if user.mfa_enabled:
        raise ValidationError(
            "A second factor is already enrolled on this account.", code="mfa_already_enrolled"
        )
    if not user.mfa_secret:
        raise ValidationError("Start the enrolment before confirming it.", code="mfa_not_started")
    if not totp.verify(user.mfa_secret, code):
        raise ValidationError(
            "That code did not match. Check the clock on the device and try the next code.",
            code="mfa_code_invalid",
        )
    user.mfa_enabled = True
    await db.flush()
    await audit_service.record(
        db,
        context,
        action="mfa.enabled",
        entity_type="user",
        entity_id=user.id,
        new_values={"mfa_enabled": True},
        reason="A second factor was enrolled and confirmed by the account holder.",
    )


async def verify_sign_in_code(user: User, code: str) -> None:
    """Check a code during sign-in. Raises rather than returning false."""
    if not user.mfa_enabled or not user.mfa_secret:
        raise PermissionDeniedError(
            "This sign-in attempt is no longer valid. Start again.",
            code="mfa_challenge_invalid",
        )
    if not totp.verify(user.mfa_secret, code):
        raise PermissionDeniedError(
            "That code did not match. Check the clock on the device and try the next code.",
            code="mfa_code_invalid",
        )


async def disable(
    db: AsyncSession,
    context: audit_service.AuditContext,
    user: User,
    *,
    password: str,
    code: str,
) -> None:
    """Remove the second factor. Both the password and a current code are required.

    Requiring both means a borrowed session cannot quietly strip the protection off an
    account, which would otherwise be the easiest way to make a stolen password useful again.
    """
    if not user.mfa_enabled:
        raise ValidationError("There is no second factor on this account.", code="mfa_not_enrolled")
    verified, _needs_rehash = passwords.verify_password(password, user.password_hash)
    if not verified:
        raise PermissionDeniedError("That password did not match.", code="invalid_credentials")
    if not totp.verify(user.mfa_secret or "", code):
        raise ValidationError(
            "That code did not match. Check the clock on the device and try the next code.",
            code="mfa_code_invalid",
        )
    user.mfa_enabled = False
    user.mfa_secret = None
    await db.flush()
    await audit_service.record(
        db,
        context,
        action="mfa.disabled",
        entity_type="user",
        entity_id=user.id,
        old_values={"mfa_enabled": True},
        new_values={"mfa_enabled": False},
        reason="The account holder removed their second factor.",
    )


async def reset_for_account(
    db: AsyncSession,
    context: audit_service.AuditContext,
    target: User,
    *,
    reason: str,
) -> None:
    """An administrator clears a second factor, for a lost or replaced device.

    This is the recovery path, and it is not silent: the reason is mandatory and the event
    names the administrator who did it.
    """
    if not target.mfa_enabled and not target.mfa_secret:
        raise ValidationError("There is no second factor on that account.", code="mfa_not_enrolled")
    target.mfa_enabled = False
    target.mfa_secret = None
    await db.flush()
    await audit_service.record(
        db,
        context,
        action="mfa.reset_by_administrator",
        entity_type="user",
        entity_id=target.id,
        old_values={"mfa_enabled": True},
        new_values={"mfa_enabled": False},
        reason=reason,
    )
