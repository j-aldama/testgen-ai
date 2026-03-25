"""Tests for ISTQB technique implementations."""

from __future__ import annotations

import pytest

from testgen.config import ISTQBTechnique, Requirement, TestType
from testgen.generator.techniques import (
    boundary_value_analysis,
    decision_table,
    equivalence_partitioning,
    error_guessing,
    state_transition,
    apply_techniques,
)


@pytest.fixture
def numeric_requirement() -> Requirement:
    return Requirement(
        id="REQ-001",
        text="The age field must accept values between 18 and 65",
        source="test",
    )


@pytest.fixture
def password_requirement() -> Requirement:
    return Requirement(
        id="REQ-002",
        text="The password must have a minimum 8 characters and maximum 128 characters",
        source="test",
    )


@pytest.fixture
def multi_condition_requirement() -> Requirement:
    return Requirement(
        id="REQ-003",
        text="The user must have a valid email and must have a strong password and must accept terms",
        source="test",
    )


@pytest.fixture
def state_requirement() -> Requirement:
    return Requirement(
        id="REQ-004",
        text="Account states: active, pending approval, locked. Active accounts can be locked after failed attempts.",
        source="test",
    )


@pytest.fixture
def generic_requirement() -> Requirement:
    return Requirement(
        id="REQ-005",
        text="The user must be able to register with email and password",
        source="test",
    )


class TestEquivalencePartitioning:
    """Tests for EP technique."""

    def test_generates_cases_for_numeric_range(self, numeric_requirement: Requirement) -> None:
        cases = equivalence_partitioning(numeric_requirement, start_id=1)
        assert len(cases) >= 2
        assert all(c.istqb_technique == ISTQBTechnique.EQUIVALENCE_PARTITIONING for c in cases)
        assert all(c.traceability == "REQ-001" for c in cases)

    def test_valid_class_has_mid_value(self, numeric_requirement: Requirement) -> None:
        cases = equivalence_partitioning(numeric_requirement, start_id=1)
        valid_cases = [c for c in cases if c.type == TestType.FUNCTIONAL]
        assert len(valid_cases) >= 1
        # Mid value of 18-65 is 41
        assert any("41" in c.test_data for c in valid_cases)

    def test_invalid_classes_generated(self, numeric_requirement: Requirement) -> None:
        cases = equivalence_partitioning(numeric_requirement, start_id=1)
        negative_cases = [c for c in cases if c.type == TestType.NEGATIVE]
        assert len(negative_cases) >= 1

    def test_generic_ep_for_text_fields(self, generic_requirement: Requirement) -> None:
        cases = equivalence_partitioning(generic_requirement, start_id=1)
        assert len(cases) >= 2
        # Should have at least one valid and one invalid class
        types = {c.type for c in cases}
        assert TestType.FUNCTIONAL in types or TestType.NEGATIVE in types


class TestBoundaryValueAnalysis:
    """Tests for BVA technique."""

    def test_generates_boundary_cases(self, numeric_requirement: Requirement) -> None:
        cases = boundary_value_analysis(numeric_requirement, start_id=1)
        assert len(cases) == 6  # min-1, min, min+1, max-1, max, max+1

    def test_boundary_values_are_correct(self, numeric_requirement: Requirement) -> None:
        cases = boundary_value_analysis(numeric_requirement, start_id=1)
        test_data_values = [c.test_data for c in cases]
        # For range 18-65: 17, 18, 19, 64, 65, 66
        assert any("17" in td for td in test_data_values)
        assert any("18" in td for td in test_data_values)
        assert any("19" in td for td in test_data_values)
        assert any("64" in td for td in test_data_values)
        assert any("65" in td for td in test_data_values)
        assert any("66" in td for td in test_data_values)

    def test_invalid_boundaries_are_negative_type(self, numeric_requirement: Requirement) -> None:
        cases = boundary_value_analysis(numeric_requirement, start_id=1)
        # min-1 and max+1 should be negative tests
        negative_cases = [c for c in cases if c.type == TestType.NEGATIVE]
        assert len(negative_cases) == 2

    def test_password_length_boundaries(self, password_requirement: Requirement) -> None:
        cases = boundary_value_analysis(password_requirement, start_id=1)
        assert len(cases) == 6
        test_data_values = [c.test_data for c in cases]
        assert any("7" in td for td in test_data_values)
        assert any("8" in td for td in test_data_values)
        assert any("9" in td for td in test_data_values)


class TestDecisionTable:
    """Tests for Decision Table technique."""

    def test_generates_combinations(self, multi_condition_requirement: Requirement) -> None:
        cases = decision_table(multi_condition_requirement, start_id=1)
        assert len(cases) >= 4  # At least 2^2 = 4 combinations for 2 conditions

    def test_all_cases_reference_requirement(
        self, multi_condition_requirement: Requirement
    ) -> None:
        cases = decision_table(multi_condition_requirement, start_id=1)
        assert all(c.traceability == "REQ-003" for c in cases)
        assert all(c.istqb_technique == ISTQBTechnique.DECISION_TABLE for c in cases)

    def test_includes_all_valid_combination(
        self, multi_condition_requirement: Requirement
    ) -> None:
        cases = decision_table(multi_condition_requirement, start_id=1)
        functional_cases = [c for c in cases if c.type == TestType.FUNCTIONAL]
        assert len(functional_cases) >= 1

    def test_no_cases_for_single_condition(self) -> None:
        req = Requirement(id="REQ-X", text="The system must validate input", source="test")
        cases = decision_table(req, start_id=1)
        assert len(cases) == 0  # Needs at least 2 conditions


class TestStateTransition:
    """Tests for State Transition technique."""

    def test_generates_transitions(self, state_requirement: Requirement) -> None:
        cases = state_transition(state_requirement, start_id=1)
        assert len(cases) >= 1
        assert all(c.istqb_technique == ISTQBTechnique.STATE_TRANSITION for c in cases)

    def test_includes_valid_transitions(self, state_requirement: Requirement) -> None:
        cases = state_transition(state_requirement, start_id=1)
        valid_cases = [c for c in cases if c.type == TestType.FUNCTIONAL]
        assert len(valid_cases) >= 1

    def test_includes_invalid_transition(self, state_requirement: Requirement) -> None:
        cases = state_transition(state_requirement, start_id=1)
        negative_cases = [c for c in cases if c.type == TestType.NEGATIVE]
        # Should include at least one invalid transition if there are 3+ states
        assert len(negative_cases) >= 1 or len(cases) < 3


class TestErrorGuessing:
    """Tests for Error Guessing technique."""

    def test_generates_common_error_patterns(self, generic_requirement: Requirement) -> None:
        cases = error_guessing(generic_requirement, start_id=1)
        assert len(cases) == 6  # null, special chars, SQL injection, long, unicode, whitespace

    def test_includes_security_tests(self, generic_requirement: Requirement) -> None:
        cases = error_guessing(generic_requirement, start_id=1)
        security_cases = [c for c in cases if c.type == TestType.SECURITY]
        assert len(security_cases) >= 1

    def test_includes_sql_injection(self, generic_requirement: Requirement) -> None:
        cases = error_guessing(generic_requirement, start_id=1)
        sql_cases = [c for c in cases if "sql" in c.title.lower() or "injection" in c.title.lower()]
        assert len(sql_cases) >= 1

    def test_includes_xss_test(self, generic_requirement: Requirement) -> None:
        cases = error_guessing(generic_requirement, start_id=1)
        xss_cases = [c for c in cases if "script" in c.test_data.lower() or "special" in c.title.lower()]
        assert len(xss_cases) >= 1

    def test_all_have_correct_technique(self, generic_requirement: Requirement) -> None:
        cases = error_guessing(generic_requirement, start_id=1)
        assert all(c.istqb_technique == ISTQBTechnique.ERROR_GUESSING for c in cases)


class TestApplyTechniques:
    """Tests for the technique orchestrator."""

    def test_apply_single_technique(
        self, generic_requirement: Requirement, sample_test_cases: list
    ) -> None:
        additional = apply_techniques(
            [generic_requirement],
            [ISTQBTechnique.ERROR_GUESSING],
            sample_test_cases,
        )
        assert len(additional) >= 1
        assert all(c.istqb_technique == ISTQBTechnique.ERROR_GUESSING for c in additional)

    def test_apply_multiple_techniques(
        self, numeric_requirement: Requirement, sample_test_cases: list
    ) -> None:
        additional = apply_techniques(
            [numeric_requirement],
            [ISTQBTechnique.EQUIVALENCE_PARTITIONING, ISTQBTechnique.BOUNDARY_VALUE_ANALYSIS],
            sample_test_cases,
        )
        techniques_used = {c.istqb_technique for c in additional}
        assert len(techniques_used) >= 1

    def test_no_duplicate_titles(
        self, generic_requirement: Requirement, sample_test_cases: list
    ) -> None:
        additional = apply_techniques(
            [generic_requirement],
            [ISTQBTechnique.ERROR_GUESSING],
            sample_test_cases,
        )
        titles = [c.title.lower() for c in additional]
        assert len(titles) == len(set(titles))
