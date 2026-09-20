"""Unit tests for the presentation layer: labels, counted nouns, and the prose gate.

These cover the wording the product shows a reader, which is as easy to get wrong as
the arithmetic and much easier to leave wrong.
"""

from __future__ import annotations

import re
from itertools import pairwise
from pathlib import Path
from typing import ClassVar

import pytest

from app.domain import labels
from app.domain.enums import (
    DECIDED_STATES,
    DeclarationType,
    InspectionState,
    LegalOutcome,
    PackageFace,
    Role,
)
from app.security import Permission, phrase_for
from app.services.phrasing import counted, plural, verb

# tests/ sits inside api/, so one level up is the api tree and two is the repository
# root. Both matter, and they are not the same thing in every environment: the built
# image holds api/ at /app with no repository above it, while a mounted checkout has the
# repository root one level up. Anchoring on tests/ gets both right.
API_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = API_ROOT.parent
WEB_UTIL = REPO_ROOT / "web" / "js" / "util.js"

# The browser sources sit outside api/, so a run that mounts api/ alone cannot see them.
# CI checks out the whole repository and these checks are authoritative there. Locally
# they say why they did not run rather than raising FileNotFoundError from a helper.
WEB_REACHABLE = WEB_UTIL.is_file()
MOUNT_HINT = (
    f"{WEB_UTIL} is not reachable. Mount the repository root rather than api/ alone: "
    'docker compose run --rm --no-deps -v "$PWD:/repo" -w /repo/api '
    "-e PYTHONPATH=/repo/api --entrypoint sh api scripts/run_tests.sh"
)


class TestLabels:
    def test_mechanical_rule_keeps_later_capitals(self) -> None:
        # str.capitalize would lower-case the rest and turn a proper noun to junk.
        assert labels.mechanical("country_of_origin") == "Country of origin"
        assert labels.mechanical("state_HR") == "State HR"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("mrp", "MRP"),
            ("mrp_close_up", "MRP close-up"),
            ("fssai_licence", "FSSAI licence"),
            ("non_compliant", "Non-compliant"),
            ("rule_admin", "Rule administrator"),
            ("ecommerce_listing", "E-commerce listing"),
            ("side_panel_left", "Left side panel"),
            ("follow_up_inspection", "Follow-up inspection"),
        ],
    )
    def test_exceptions_are_applied(self, value: str, expected: str) -> None:
        assert labels.label_for(value) == expected

    def test_no_label_is_left_looking_mechanical(self) -> None:
        """No label may contain an underscore or a lower-case acronym."""
        for enum_class in (PackageFace, DeclarationType, LegalOutcome, Role, InspectionState):
            for option in labels.options(enum_class):
                label = option["label"]
                assert "_" not in label, f"{option['value']} label still has an underscore"
                assert not label.startswith("Mrp"), f"{option['value']} label reads as Mrp"
                assert not label.startswith("Fssai"), f"{option['value']} label reads as Fssai"

    def test_every_override_matches_a_real_enum_value(self) -> None:
        """A stale override is worse than none: it never fires and hides a typo."""
        known = set()
        for enum_class in (
            PackageFace,
            DeclarationType,
            LegalOutcome,
            Role,
            InspectionState,
        ):
            known.update(member.value for member in enum_class)
        # These are not enum members. They are values carried on records:
        # complaint categories, case states, notice types, evidence kinds and the
        # party_role column, all of which the reports label through the same table.
        allowed_extras = {
            "mrp_overcharge",
            "ocr_input",
            "date_marking_close_up",
            "net_quantity_close_up",
            "mrp_close_up",
            "follow_up_inspection",
            "show_cause",
            "ecommerce_listing",
            "expired_or_date_issue",
        }
        for value in labels.OVERRIDES:
            assert value in known or value in allowed_extras, f"override {value!r} is stale"

    def test_decision_options_are_exactly_the_decided_states(self) -> None:
        """The choices offered must be the choices the service accepts.

        The browser used to populate this select from LegalOutcome, which offered
        three values POST /inspections/{id}/decision rejects and omitted
        "violation found" entirely.
        """
        offered = {
            option["value"]
            for option in labels.options_for(
                tuple(state.value for state in InspectionState if state in DECIDED_STATES)
            )
        }
        assert offered == {state.value for state in DECIDED_STATES}
        assert "violation_found" in offered
        assert "not_applicable" not in offered


@pytest.mark.skipif(not WEB_REACHABLE, reason=MOUNT_HINT)
class TestJavaScriptLabelParity:
    """web/js/util.js keeps its own copy of the override table. Prove they agree.

    A few values are rendered without a vocabulary lookup, so the browser needs the
    table locally. Duplication is acceptable only while it is checked.
    """

    @staticmethod
    def _parse_js_overrides() -> dict[str, str]:
        source = WEB_UTIL.read_text(encoding="utf-8")
        block = re.search(r"export const LABEL_OVERRIDES = \{(.*?)\n\};", source, re.DOTALL)
        assert block, "LABEL_OVERRIDES not found in web/js/util.js"
        pairs = re.findall(r"^\s*([A-Za-z_][\w]*)\s*:\s*'([^']*)',", block.group(1), re.MULTILINE)
        return dict(pairs)

    def test_tables_are_identical(self) -> None:
        assert self._parse_js_overrides() == labels.OVERRIDES


class TestPhrasing:
    @pytest.mark.parametrize(
        ("noun", "count", "expected"),
        [
            ("test", 1, "test"),
            ("test", 2, "tests"),
            ("test", 0, "tests"),
            ("finding", 3, "findings"),
            ("category", 2, "categories"),
            ("analysis", 2, "analyses"),
            ("class", 2, "classes"),
            ("day", 2, "days"),
        ],
    )
    def test_plural_forms(self, noun: str, count: int, expected: str) -> None:
        assert plural(noun, count) == expected

    def test_counted_never_emits_the_parenthesised_s(self) -> None:
        assert counted(1, "test") == "1 test"
        assert counted(4, "test") == "4 tests"
        assert "(s)" not in counted(1, "machine reading")

    def test_verb_agreement(self) -> None:
        assert verb(1, "is", "are") == "is"
        assert verb(2, "is", "are") == "are"


class TestNoEmDashInSource:
    """The em dash is banned project-wide, so the ban is a test and not a habit.

    check_prose.py enforces this for pages and documents. This covers the source the
    prose checker does not read: Python, JavaScript and CSS.
    """

    EM_DASH = "\u2014"
    # Vendored third party, unmodified under the MPL, and never served to a user.
    SKIP: ClassVar[set[str]] = {"axe.min.js"}

    def test_source_files_are_clean(self) -> None:
        roots = [API_ROOT / "app", API_ROOT / "scripts", REPO_ROOT / "web"]
        offenders: list[str] = []
        scanned = 0
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.name in self.SKIP:
                    continue
                if path.suffix not in {".py", ".js", ".css", ".html"}:
                    continue
                scanned += 1
                if self.EM_DASH in path.read_text(encoding="utf-8"):
                    offenders.append(str(path))
        # A mis-mounted run would otherwise scan nothing and pass, which is the one
        # outcome worse than failing: a green check that proves nothing.
        assert scanned > 40, f"only {scanned} files were scanned. {MOUNT_HINT}"
        assert offenders == [], f"em dash found in: {offenders}"

    @pytest.mark.skipif(not WEB_REACHABLE, reason=MOUNT_HINT)
    def test_the_browser_sources_were_included(self) -> None:
        """Prove the scan above actually covered web/, not just the Python."""
        web_files = [
            path
            for path in (REPO_ROOT / "web").rglob("*")
            if path.is_file() and path.suffix in {".js", ".css", ".html"}
        ]
        assert len(web_files) > 30, f"found only {len(web_files)} browser sources"


class TestNoRawEnumInFindingText:
    """A finding explanation is read by an officer and printed on the report.

    The incomplete-evidence branch joined PackageFace values straight into the sentence,
    so the inspection screen said "(principal_display_panel outstanding)". That names the
    enum member rather than the panel, and no existing check covered it:
    check_error_messages.py inspects raise statements, and this is an explanation, not an
    error. These tests close that gap from both directions.
    """

    @staticmethod
    def _explanation(face: str) -> str:
        from app.services.rules.checks import CheckInput, check_declaration_present

        payload = CheckInput(
            values={},
            parameters={"declaration": DeclarationType.NET_QUANTITY.value, "label": "Net quantity"},
            evidence_complete=False,
            missing_faces=[face],
        )
        return check_declaration_present(payload).explanation

    def test_the_panel_is_named_in_words(self) -> None:
        face = PackageFace.PRINCIPAL_DISPLAY_PANEL.value
        explanation = self._explanation(face)
        assert face not in explanation, "the raw enum value reached the officer: " + explanation
        assert labels.label_for(face) in explanation

    @pytest.mark.parametrize("face", [f.value for f in PackageFace if "_" in f.value])
    def test_no_face_value_appears_raw(self, face: str) -> None:
        """Every multi-word face, not only the one that was found broken."""
        explanation = self._explanation(face)
        assert face not in explanation, f"{face} reached the officer verbatim"
        assert labels.label_for(face) in explanation


class TestProductLabel:
    """Brand and product name on one line.

    Joining the two columns unconditionally printed "Riverside Riverside Iodised Salt
    1 kg" on the reports register, because most packs are named with the brand in front.
    The browser had already been fixed; the API had two copies that had not.
    """

    @pytest.mark.parametrize(
        ("brand", "name", "expected"),
        [
            # The case that was found broken.
            ("Riverside", "Riverside Iodised Salt 1 kg", "Riverside Iodised Salt 1 kg"),
            # Capitalisation must not defeat the comparison.
            ("riverside", "Riverside Iodised Salt 1 kg", "Riverside Iodised Salt 1 kg"),
            ("RIVERSIDE", "Riverside Iodised Salt", "Riverside Iodised Salt"),
            # A brand that is genuinely absent from the name is still prefixed.
            ("Riverside", "Iodised Salt 1 kg", "Riverside Iodised Salt 1 kg"),
            # A brand that merely shares an opening word is not a prefix of the name.
            ("Riverside Foods", "Riverside Iodised Salt", "Riverside Foods Riverside Iodised Salt"),
            # Either side missing, and both.
            ("Riverside", "", "Riverside"),
            ("", "Iodised Salt", "Iodised Salt"),
            (None, "Iodised Salt", "Iodised Salt"),
            ("Riverside", None, "Riverside"),
            (None, None, ""),
            # Surrounding space is not a difference a reader should see.
            ("  Riverside  ", "  Riverside Iodised Salt  ", "Riverside Iodised Salt"),
        ],
    )
    def test_the_brand_is_never_repeated(
        self, brand: str | None, name: str | None, expected: str
    ) -> None:
        assert labels.product_label(brand, name) == expected

    def test_no_result_opens_with_a_doubled_word(self) -> None:
        """The property, rather than the cases: whatever comes out reads once."""
        for brand, name in (
            ("Riverside", "Riverside Iodised Salt 1 kg"),
            ("Testbrand", "Testbrand Test Iodised Salt 1 kg"),
            ("Tata", "Tata Salt"),
        ):
            words = labels.product_label(brand, name).split()
            doubled = [a for a, b in pairwise(words) if a.casefold() == b.casefold()]
            assert not doubled, f"{brand} + {name} produced a doubled word: {doubled}"


@pytest.mark.skipif(not WEB_REACHABLE, reason=MOUNT_HINT)
class TestProductLabelParity:
    """web/js/util.js composes the same label for values the browser builds itself.

    Two implementations of one rule is acceptable only while something checks that they
    agree, so the guard the browser applies is asserted to be present rather than taken
    on trust.
    """

    def test_the_browser_applies_the_same_prefix_guard(self) -> None:
        source = WEB_UTIL.read_text(encoding="utf-8")
        block = re.search(r"export function productLabel\(p\) \{(.*?)\n\}", source, re.DOTALL)
        assert block, "productLabel not found in web/js/util.js"
        body = block.group(1)
        assert "startsWith" in body, "the browser no longer guards against a repeated brand"
        assert "toLowerCase" in body, "the browser's comparison is case sensitive again"


class TestPermissionPhrasing:
    """A denial message is read by an officer, not by a developer.

    It interpolated the raw permission, so a reviewer who opened the audit screen was
    told "Your role does not permit audit.read". check_error_messages.py could not catch
    it: the value arrives at runtime, so the source holds no dotted token to find.
    """

    @pytest.mark.parametrize("permission", list(Permission))
    def test_every_permission_has_a_phrase(self, permission: Permission) -> None:
        phrase = phrase_for(permission)
        assert phrase != "this action", (
            f"{permission.value} has no phrase, so its denial falls back to the generic "
            "wording. Add its subject or action in app/security/permissions.py."
        )

    @pytest.mark.parametrize("permission", list(Permission))
    def test_no_machine_identifier_reaches_the_officer(self, permission: Permission) -> None:
        message = f"Your role does not permit {phrase_for(permission)}."
        assert "." not in message[:-1], f"a dotted identifier survived: {message}"
        assert "_" not in message, f"an underscored identifier survived: {message}"
        assert permission.value not in message

    def test_the_message_reads_as_a_sentence(self) -> None:
        assert (
            f"Your role does not permit {phrase_for(Permission.AUDIT_READ)}."
            == "Your role does not permit reading the audit trail."
        )

    def test_the_denial_raised_by_the_guard_carries_the_phrase(self) -> None:
        from app.errors import PermissionDeniedError
        from app.security.permissions import require_permission

        with pytest.raises(PermissionDeniedError) as raised:
            require_permission(Role.REVIEWER, Permission.AUDIT_READ)
        assert "reading the audit trail" in str(raised.value)
        # The machine name stays available to a caller, just not in the sentence.
        assert raised.value.details == {
            "required_permission": "audit.read",
            "role": "reviewer",
        }

    def test_an_unknown_permission_falls_back_rather_than_leaking(self) -> None:
        assert phrase_for("nonesuch.frobnicate") == "this action"
