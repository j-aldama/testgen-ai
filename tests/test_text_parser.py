"""Tests for text_parser module."""

from __future__ import annotations

import pytest

from testgen.parser.text_parser import detect_format, parse_requirements


class TestDetectFormat:
    """Tests for format detection."""

    def test_detect_gherkin_with_scenario(self) -> None:
        text = "Scenario: User logs in\n  Given the user is on login page"
        assert detect_format(text) == "gherkin"

    def test_detect_gherkin_with_feature(self) -> None:
        text = "Feature: Authentication\n  Scenario: Login"
        assert detect_format(text) == "gherkin"

    def test_detect_structured_numbered(self) -> None:
        text = "1. The system shall validate input\n2. The system shall log errors"
        assert detect_format(text) == "structured"

    def test_detect_structured_bullets(self) -> None:
        text = "- The system must authenticate users\n- The system must authorize"
        assert detect_format(text) == "structured"

    def test_detect_freeform(self) -> None:
        text = "The system should handle user authentication securely."
        assert detect_format(text) == "freeform"


class TestParseRequirements:
    """Tests for requirement parsing."""

    def test_parse_empty_text(self) -> None:
        result = parse_requirements("")
        assert result == []

    def test_parse_numbered_list(self) -> None:
        text = (
            "1. The user must be able to register with email and password.\n"
            "2. The password must have a minimum of 8 characters.\n"
            "3. The email must be unique in the system."
        )
        result = parse_requirements(text)
        assert len(result) == 3
        assert result[0].id == "REQ-001"
        assert "register" in result[0].text.lower()
        assert result[1].id == "REQ-002"
        assert "password" in result[1].text.lower()

    def test_parse_bullet_list(self) -> None:
        text = (
            "- Users can search products by name\n"
            "- Users can filter products by category\n"
            "- Users can sort results by price"
        )
        result = parse_requirements(text)
        assert len(result) == 3
        assert all(r.source == "user_input" for r in result)

    def test_parse_freeform_sentences(self) -> None:
        text = (
            "The system must validate all user inputs. "
            "Invalid inputs should display appropriate error messages."
        )
        result = parse_requirements(text)
        assert len(result) >= 1
        assert all(len(r.text) > 10 for r in result)

    def test_parse_paragraphs(self) -> None:
        text = (
            "The login page must accept email and password.\n\n"
            "After 3 failed attempts, the account is locked.\n\n"
            "Locked accounts require admin intervention to unlock."
        )
        result = parse_requirements(text)
        assert len(result) == 3

    def test_parse_gherkin_scenarios(self) -> None:
        text = (
            "Scenario: Valid login\n"
            "  Given the user is on the login page\n"
            "  When they enter valid credentials\n"
            "  Then they are redirected to the dashboard\n\n"
            "Scenario: Invalid login\n"
            "  Given the user is on the login page\n"
            "  When they enter invalid credentials\n"
            "  Then an error message is shown"
        )
        result = parse_requirements(text)
        assert len(result) == 2
        assert "Valid login" in result[0].text
        assert "Invalid login" in result[1].text

    def test_parse_with_custom_source(self) -> None:
        text = "1. Users must authenticate before accessing the dashboard."
        result = parse_requirements(text, source="prd.md")
        assert result[0].source == "prd.md"

    def test_parse_short_text_ignored(self) -> None:
        text = "Short."
        result = parse_requirements(text)
        assert result == []

    def test_parse_mixed_formats(self) -> None:
        text = (
            "1. The system shall process payments securely.\n"
            "2. All transactions must be logged for audit purposes.\n"
            "3. Failed payments should trigger a notification to the user."
        )
        result = parse_requirements(text)
        assert len(result) == 3
        for req in result:
            assert req.id.startswith("REQ-")
            assert len(req.text) > 10

    def test_requirement_ids_are_sequential(self) -> None:
        text = (
            "- First requirement here for testing purposes\n"
            "- Second requirement here for testing purposes\n"
            "- Third requirement here for testing purposes"
        )
        result = parse_requirements(text)
        ids = [r.id for r in result]
        assert ids == ["REQ-001", "REQ-002", "REQ-003"]
