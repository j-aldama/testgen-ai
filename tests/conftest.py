"""Shared fixtures for TestGen tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    Priority,
    Requirement,
    Step,
    TestCase,
    TestType,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_requirements() -> list[Requirement]:
    """Return a list of sample requirements for testing."""
    return [
        Requirement(
            id="REQ-001",
            text="The user must be able to register with email and password",
            source="test",
        ),
        Requirement(
            id="REQ-002",
            text="The password must have a minimum of 8 characters and a maximum of 128 characters",
            source="test",
        ),
        Requirement(
            id="REQ-003",
            text="The email must be unique in the system",
            source="test",
        ),
    ]


@pytest.fixture
def sample_test_cases() -> list[TestCase]:
    """Return a list of sample test cases for testing."""
    return [
        TestCase(
            id="TC-001",
            title="Valid registration with correct email and password",
            preconditions="User is on the registration page",
            steps=[
                Step(
                    given="User is on the registration page",
                    when="User enters valid email 'test@example.com' and password 'SecureP@ss1'",
                    then="Registration is successful and user receives confirmation",
                )
            ],
            test_data="email=test@example.com, password=SecureP@ss1",
            expected_result="User account is created successfully",
            priority=Priority.HIGH,
            type=TestType.FUNCTIONAL,
            istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
            traceability="REQ-001",
        ),
        TestCase(
            id="TC-002",
            title="Registration with password below minimum length",
            preconditions="User is on the registration page",
            steps=[
                Step(
                    given="User is on the registration page",
                    when="User enters password with 7 characters",
                    then="System shows validation error for password length",
                )
            ],
            test_data="email=test@example.com, password=Short1!",
            expected_result="Error: Password must be at least 8 characters",
            priority=Priority.HIGH,
            type=TestType.BOUNDARY,
            istqb_technique=ISTQBTechnique.BOUNDARY_VALUE_ANALYSIS,
            traceability="REQ-002",
        ),
        TestCase(
            id="TC-003",
            title="Registration with duplicate email",
            preconditions="User 'existing@example.com' already exists in the system",
            steps=[
                Step(
                    given="A user with email 'existing@example.com' already exists",
                    when="New user tries to register with 'existing@example.com'",
                    then="System shows error about duplicate email",
                )
            ],
            test_data="email=existing@example.com, password=ValidP@ss1",
            expected_result="Error: Email already registered",
            priority=Priority.HIGH,
            type=TestType.NEGATIVE,
            istqb_technique=ISTQBTechnique.ERROR_GUESSING,
            traceability="REQ-003",
        ),
    ]


@pytest.fixture
def sample_generation_result(
    sample_requirements: list[Requirement],
    sample_test_cases: list[TestCase],
) -> GenerationResult:
    """Return a sample GenerationResult for testing."""
    return GenerationResult(
        session_id="test-session-123",
        requirements=sample_requirements,
        test_cases=sample_test_cases,
    )


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR
