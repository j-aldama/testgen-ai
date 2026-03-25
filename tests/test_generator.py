"""Tests for the test case generator (with mocked LLM)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    Priority,
    Requirement,
    TestType,
)
from testgen.generator.llm_client import BaseLLMClient, parse_json_response
from testgen.generator.test_case_generator import TestCaseGenerator, _parse_raw_test_cases


# Sample LLM response simulating Claude output
MOCK_LLM_RESPONSE = [
    {
        "id": "TC-001",
        "title": "Valid registration with correct email and password",
        "preconditions": "User is on the registration page",
        "steps": [
            {
                "given": "User is on the registration page",
                "when": "User enters email 'user@example.com' and password 'Str0ngP@ss!'",
                "then": "Account is created and confirmation email is sent",
            }
        ],
        "test_data": "email=user@example.com, password=Str0ngP@ss!",
        "expected_result": "User account is created successfully",
        "priority": "High",
        "type": "Functional",
        "istqb_technique": "Equivalence Partitioning",
        "traceability": "REQ-001",
    },
    {
        "id": "TC-002",
        "title": "Registration with invalid email format",
        "preconditions": "User is on the registration page",
        "steps": [
            {
                "given": "User is on the registration page",
                "when": "User enters 'not-an-email' as email",
                "then": "System shows email validation error",
            }
        ],
        "test_data": "email=not-an-email, password=Str0ngP@ss!",
        "expected_result": "Error: Invalid email format",
        "priority": "High",
        "type": "Negative",
        "istqb_technique": "Equivalence Partitioning",
        "traceability": "REQ-001",
    },
    {
        "id": "TC-003",
        "title": "Password at minimum boundary (8 characters)",
        "preconditions": "User is on the registration page",
        "steps": [
            {
                "given": "User is on the registration page",
                "when": "User enters a password with exactly 8 characters",
                "then": "Password is accepted",
            }
        ],
        "test_data": "email=test@test.com, password=Pass123!",
        "expected_result": "Password meets minimum length requirement",
        "priority": "Medium",
        "type": "Boundary",
        "istqb_technique": "Boundary Value Analysis",
        "traceability": "REQ-002",
    },
]


class TestParseJsonResponse:
    """Tests for JSON response parsing."""

    def test_parse_valid_json_array(self) -> None:
        text = '[{"id": "TC-001", "title": "Test"}]'
        result = parse_json_response(text)
        assert len(result) == 1
        assert result[0]["id"] == "TC-001"

    def test_parse_json_in_code_block(self) -> None:
        text = '```json\n[{"id": "TC-001", "title": "Test"}]\n```'
        result = parse_json_response(text)
        assert len(result) == 1

    def test_parse_json_with_wrapper(self) -> None:
        text = '{"test_cases": [{"id": "TC-001"}]}'
        result = parse_json_response(text)
        assert len(result) == 1

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="could not be parsed"):
            parse_json_response("This is not JSON at all")

    def test_parse_json_with_extra_text(self) -> None:
        text = 'Here are the test cases:\n[{"id": "TC-001", "title": "Test"}]\nDone!'
        result = parse_json_response(text)
        assert len(result) == 1


class TestParseRawTestCases:
    """Tests for converting raw LLM output to TestCase objects."""

    def test_parse_valid_response(self, sample_requirements: list[Requirement]) -> None:
        cases = _parse_raw_test_cases(MOCK_LLM_RESPONSE, sample_requirements)
        assert len(cases) == 3
        assert cases[0].title == "Valid registration with correct email and password"
        assert cases[0].priority == Priority.HIGH
        assert cases[0].type == TestType.FUNCTIONAL
        assert cases[0].istqb_technique == ISTQBTechnique.EQUIVALENCE_PARTITIONING

    def test_steps_are_parsed(self, sample_requirements: list[Requirement]) -> None:
        cases = _parse_raw_test_cases(MOCK_LLM_RESPONSE, sample_requirements)
        assert len(cases[0].steps) == 1
        assert cases[0].steps[0].given == "User is on the registration page"

    def test_traceability_validated(self, sample_requirements: list[Requirement]) -> None:
        cases = _parse_raw_test_cases(MOCK_LLM_RESPONSE, sample_requirements)
        for tc in cases:
            assert tc.traceability in {"REQ-001", "REQ-002", "REQ-003"}

    def test_malformed_entry_skipped(self, sample_requirements: list[Requirement]) -> None:
        # The parser is forgiving — it fills defaults, so even minimal dicts work
        raw = [{"id": "TC-001"}]
        cases = _parse_raw_test_cases(raw, sample_requirements)
        assert len(cases) == 1
        assert cases[0].title == "Test Case 1"

    def test_unknown_priority_defaults(self, sample_requirements: list[Requirement]) -> None:
        raw = [{"id": "TC-001", "priority": "Unknown", "type": "Unknown"}]
        cases = _parse_raw_test_cases(raw, sample_requirements)
        assert cases[0].priority == Priority.MEDIUM
        assert cases[0].type == TestType.FUNCTIONAL


class TestTestCaseGenerator:
    """Tests for the full generation pipeline with mocked LLM."""

    def test_generate_with_mocked_llm(self, sample_requirements: list[Requirement]) -> None:
        mock_client = MagicMock(spec=BaseLLMClient)
        mock_client.generate.return_value = MOCK_LLM_RESPONSE

        generator = TestCaseGenerator(llm_client=mock_client)
        result = generator.generate(sample_requirements)

        assert isinstance(result, GenerationResult)
        assert len(result.test_cases) == 3
        assert result.requirements == sample_requirements
        mock_client.generate.assert_called_once()

    def test_generate_with_techniques_adds_cases(
        self, sample_requirements: list[Requirement]
    ) -> None:
        mock_client = MagicMock(spec=BaseLLMClient)
        mock_client.generate.return_value = MOCK_LLM_RESPONSE

        generator = TestCaseGenerator(llm_client=mock_client)
        result = generator.generate(
            sample_requirements,
            techniques=[ISTQBTechnique.ERROR_GUESSING],
        )

        # Should have original 3 + additional from error guessing
        assert len(result.test_cases) > 3

    def test_generate_renumbers_ids(self, sample_requirements: list[Requirement]) -> None:
        mock_client = MagicMock(spec=BaseLLMClient)
        mock_client.generate.return_value = MOCK_LLM_RESPONSE

        generator = TestCaseGenerator(llm_client=mock_client)
        result = generator.generate(sample_requirements)

        ids = [tc.id for tc in result.test_cases]
        assert ids == ["TC-001", "TC-002", "TC-003"]

    def test_generate_empty_requirements_raises(self) -> None:
        mock_client = MagicMock(spec=BaseLLMClient)
        generator = TestCaseGenerator(llm_client=mock_client)

        with pytest.raises(ValueError, match="No requirements"):
            generator.generate([])

    def test_generate_without_client_raises(
        self, sample_requirements: list[Requirement]
    ) -> None:
        generator = TestCaseGenerator(llm_client=None)

        with pytest.raises(ValueError, match="LLM client"):
            generator.generate(sample_requirements)

    def test_summary_is_correct(self, sample_requirements: list[Requirement]) -> None:
        mock_client = MagicMock(spec=BaseLLMClient)
        mock_client.generate.return_value = MOCK_LLM_RESPONSE

        generator = TestCaseGenerator(llm_client=mock_client)
        result = generator.generate(sample_requirements)

        summary = result.summary
        assert summary["total"] == 3
        assert summary["requirements_count"] == 3
        assert "High" in summary["by_priority"]
        assert "Functional" in summary["by_type"]
