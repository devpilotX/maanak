"""Unit tests for the second factor.

The RFC 6238 test vectors are the whole point of this file. An implementation of TOTP that
is nearly right produces codes an authenticator application rejects, and the only way to know
it is right is to check it against the values the standard publishes.
"""

from __future__ import annotations

import base64

import pytest

from app.security import totp

#: RFC 6238 Appendix B, the SHA-1 rows. The seed is the ASCII string "12345678901234567890".
#: The RFC prints eight digits; this implementation emits six, which are the last six.
RFC_SEED = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
RFC_VECTORS = (
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
)


class TestRfc6238Vectors:
    @pytest.mark.parametrize(("seconds", "eight_digit"), RFC_VECTORS)
    def test_published_vectors(self, seconds: int, eight_digit: str) -> None:
        expected = eight_digit[-totp.DIGITS :]
        assert totp.code_at(RFC_SEED, counter=seconds // totp.STEP_SECONDS) == expected

    def test_parameters_match_what_authenticators_implement(self) -> None:
        """Changing any of these silently breaks half the authenticator applications."""
        assert totp.DIGITS == 6
        assert totp.STEP_SECONDS == 30
        assert totp.SECRET_BYTES >= 20


class TestVerification:
    def test_the_current_code_is_accepted(self) -> None:
        secret = totp.generate_secret()
        assert totp.verify(secret, totp.current_code(secret, at=1_700_000_000), at=1_700_000_000)

    @pytest.mark.parametrize("offset", [-1, 0, 1])
    def test_adjacent_steps_are_accepted(self, offset: int) -> None:
        """A phone clock and a server clock are never exactly aligned."""
        secret = totp.generate_secret()
        now = 1_700_000_000
        step = now // totp.STEP_SECONDS
        assert totp.verify(secret, totp.code_at(secret, counter=step + offset), at=now)

    @pytest.mark.parametrize("offset", [-5, -2, 2, 5, 100])
    def test_distant_steps_are_refused(self, offset: int) -> None:
        """The window is small on purpose: a wide one multiplies the valid codes."""
        secret = totp.generate_secret()
        now = 1_700_000_000
        step = now // totp.STEP_SECONDS
        assert not totp.verify(secret, totp.code_at(secret, counter=step + offset), at=now)

    @pytest.mark.parametrize("candidate", ["", "abcdef", "12345", "1234567890123", "  ", "00000a"])
    def test_malformed_candidates_are_refused(self, candidate: str) -> None:
        secret = totp.generate_secret()
        assert not totp.verify(secret, candidate)

    def test_an_empty_secret_never_verifies(self) -> None:
        """A user row with no secret must not accept any code."""
        assert not totp.verify("", "123456")

    def test_a_malformed_secret_fails_closed(self) -> None:
        assert not totp.verify("not-valid-base32-!!!", "123456")

    def test_a_code_for_another_secret_is_refused(self) -> None:
        first = totp.generate_secret()
        second = totp.generate_secret()
        now = 1_700_000_000
        assert not totp.verify(first, totp.current_code(second, at=now), at=now)


class TestSecrets:
    def test_secrets_are_unique(self) -> None:
        assert len({totp.generate_secret() for _ in range(50)}) == 50

    def test_secrets_are_decodable_base32(self) -> None:
        secret = totp.generate_secret()
        assert secret.isupper() or secret.isalnum()
        # Round-trips through the verifier, which is what proves the padding is handled.
        assert totp.verify(secret, totp.current_code(secret))


class TestProvisioningUri:
    def test_it_carries_what_an_authenticator_needs(self) -> None:
        secret = totp.generate_secret()
        uri = totp.provisioning_uri(secret=secret, account="officer@example.org", issuer="Maanak")
        assert uri.startswith("otpauth://totp/")
        assert f"secret={secret}" in uri
        assert "issuer=Maanak" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_the_label_is_escaped(self) -> None:
        """An unescaped @ or : in the label breaks the entry in the application."""
        uri = totp.provisioning_uri(secret="AAAA", account="a@b.org", issuer="Maanak")
        assert "Maanak%3Aa%40b.org" in uri
