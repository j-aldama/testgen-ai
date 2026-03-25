"""ISTQB technique implementations for enriching test case generation.

Each technique analyzes requirements and produces additional test cases
that specifically target the technique's coverage criteria.
"""

from __future__ import annotations

import re

from testgen.config import (
    ISTQBTechnique,
    Priority,
    Requirement,
    Step,
    StepFormat,
    TestCase,
    TestType,
)


def apply_techniques(
    requirements: list[Requirement],
    techniques: list[ISTQBTechnique],
    existing_test_cases: list[TestCase],
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Apply selected ISTQB techniques to generate additional test cases.

    Analyzes existing test cases to avoid duplicates and fills gaps.
    """
    additional: list[TestCase] = []
    next_id = len(existing_test_cases) + 1

    technique_funcs = {
        ISTQBTechnique.EQUIVALENCE_PARTITIONING: equivalence_partitioning,
        ISTQBTechnique.BOUNDARY_VALUE_ANALYSIS: boundary_value_analysis,
        ISTQBTechnique.DECISION_TABLE: decision_table,
        ISTQBTechnique.STATE_TRANSITION: state_transition,
        ISTQBTechnique.ERROR_GUESSING: error_guessing,
    }

    existing_titles = {tc.title.lower() for tc in existing_test_cases}

    for technique in techniques:
        func = technique_funcs.get(technique)
        if func is None:
            continue
        for req in requirements:
            new_cases = func(req, next_id, step_format)
            for tc in new_cases:
                if tc.title.lower() not in existing_titles:
                    additional.append(tc)
                    existing_titles.add(tc.title.lower())
                    next_id += 1

    return additional


def equivalence_partitioning(
    req: Requirement,
    start_id: int,
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Generate test cases using Equivalence Partitioning.

    Identifies input domains and creates one test per equivalence class:
    valid class, invalid class (too low), invalid class (too high), invalid type.
    """
    cases: list[TestCase] = []
    numeric_constraints = _extract_numeric_constraints(req.text)

    if numeric_constraints:
        for field_name, min_val, max_val in numeric_constraints:
            mid = (min_val + max_val) // 2
            cases.append(
                TestCase(
                    id=f"TC-{start_id + len(cases):03d}",
                    title=f"EP Valid: {field_name} within valid range ({mid})",
                    preconditions=f"System accepts {field_name} input",
                    steps=[
                        _make_step(
                            f"User is on the form with {field_name} field",
                            f"User enters {mid} for {field_name}",
                            f"System accepts the input",
                            step_format,
                        )
                    ],
                    test_data=f"{field_name}={mid}",
                    expected_result=f"Input {mid} is accepted as valid {field_name}",
                    priority=Priority.HIGH,
                    type=TestType.FUNCTIONAL,
                    istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
                    traceability=req.id,
                )
            )
            cases.append(
                TestCase(
                    id=f"TC-{start_id + len(cases):03d}",
                    title=f"EP Invalid Low: {field_name} below minimum ({min_val - 5})",
                    preconditions=f"System accepts {field_name} input",
                    steps=[
                        _make_step(
                            f"User is on the form with {field_name} field",
                            f"User enters {min_val - 5} for {field_name}",
                            f"System rejects the input with validation error",
                            step_format,
                        )
                    ],
                    test_data=f"{field_name}={min_val - 5}",
                    expected_result=f"Error message: {field_name} must be at least {min_val}",
                    priority=Priority.HIGH,
                    type=TestType.NEGATIVE,
                    istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
                    traceability=req.id,
                )
            )
            cases.append(
                TestCase(
                    id=f"TC-{start_id + len(cases):03d}",
                    title=f"EP Invalid High: {field_name} above maximum ({max_val + 5})",
                    preconditions=f"System accepts {field_name} input",
                    steps=[
                        _make_step(
                            f"User is on the form with {field_name} field",
                            f"User enters {max_val + 5} for {field_name}",
                            f"System rejects the input with validation error",
                            step_format,
                        )
                    ],
                    test_data=f"{field_name}={max_val + 5}",
                    expected_result=f"Error message: {field_name} must be at most {max_val}",
                    priority=Priority.MEDIUM,
                    type=TestType.NEGATIVE,
                    istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
                    traceability=req.id,
                )
            )
    else:
        # Generic EP for text fields
        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"EP Valid: Valid input for {_short_title(req.text)}",
                preconditions="System is ready to accept input",
                steps=[
                    _make_step(
                        "User is on the input form",
                        "User provides valid input matching requirements",
                        "System processes the input successfully",
                        step_format,
                    )
                ],
                test_data="Valid representative input value",
                expected_result="Input is accepted and processed correctly",
                priority=Priority.HIGH,
                type=TestType.FUNCTIONAL,
                istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
                traceability=req.id,
            )
        )
        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"EP Invalid: Empty input for {_short_title(req.text)}",
                preconditions="System is ready to accept input",
                steps=[
                    _make_step(
                        "User is on the input form",
                        "User submits empty/blank input",
                        "System shows validation error",
                        step_format,
                    )
                ],
                test_data="(empty string)",
                expected_result="Validation error: field is required",
                priority=Priority.HIGH,
                type=TestType.NEGATIVE,
                istqb_technique=ISTQBTechnique.EQUIVALENCE_PARTITIONING,
                traceability=req.id,
            )
        )

    return cases


def boundary_value_analysis(
    req: Requirement,
    start_id: int,
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Generate test cases using Boundary Value Analysis.

    Tests at exact boundaries: min-1, min, min+1, max-1, max, max+1.
    """
    cases: list[TestCase] = []
    numeric_constraints = _extract_numeric_constraints(req.text)

    if not numeric_constraints:
        # Look for length constraints like "minimum X characters"
        length_match = re.search(
            r"(?:minim(?:um|o)|at least|min)\s+(\d+)\s+(?:character|char|digit|letra)",
            req.text,
            re.IGNORECASE,
        )
        max_match = re.search(
            r"(?:maxim(?:um|o)|at most|max|up to)\s+(\d+)\s+(?:character|char|digit|letra)",
            req.text,
            re.IGNORECASE,
        )
        if length_match:
            min_val = int(length_match.group(1))
            max_val = int(max_match.group(1)) if max_match else min_val + 50
            numeric_constraints = [("length", min_val, max_val)]

    for field_name, min_val, max_val in numeric_constraints:
        boundary_points = [
            (min_val - 1, "below minimum", False),
            (min_val, "at minimum", True),
            (min_val + 1, "just above minimum", True),
            (max_val - 1, "just below maximum", True),
            (max_val, "at maximum", True),
            (max_val + 1, "above maximum", False),
        ]
        for value, desc, is_valid in boundary_points:
            expected = "accepted" if is_valid else "rejected with validation error"
            tc_type = TestType.BOUNDARY if is_valid else TestType.NEGATIVE
            priority = Priority.HIGH if not is_valid else Priority.MEDIUM
            cases.append(
                TestCase(
                    id=f"TC-{start_id + len(cases):03d}",
                    title=f"BVA: {field_name} {desc} ({value})",
                    preconditions=f"System validates {field_name}",
                    steps=[
                        _make_step(
                            f"User is entering {field_name}",
                            f"User inputs value {value} ({desc})",
                            f"Input is {expected}",
                            step_format,
                        )
                    ],
                    test_data=f"{field_name}={value}",
                    expected_result=f"Value {value} ({desc}) is {expected}",
                    priority=priority,
                    type=tc_type,
                    istqb_technique=ISTQBTechnique.BOUNDARY_VALUE_ANALYSIS,
                    traceability=req.id,
                )
            )

    return cases


def decision_table(
    req: Requirement,
    start_id: int,
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Generate test cases using Decision Table technique.

    Identifies conditions in the requirement and creates combinations.
    """
    cases: list[TestCase] = []
    conditions = _extract_conditions(req.text)

    if len(conditions) < 2:
        # Need at least 2 conditions for a meaningful decision table
        return cases

    # Generate key combinations (up to 4 conditions = 16 combos max)
    capped_conditions = conditions[:4]
    combos = _generate_combinations(capped_conditions)

    for i, combo in enumerate(combos):
        combo_desc = ", ".join(
            f"{cond}={'Valid' if val else 'Invalid'}" for cond, val in zip(capped_conditions, combo)
        )
        all_valid = all(combo)
        expected = "Operation succeeds" if all_valid else "Operation fails with appropriate error"
        priority = Priority.HIGH if all_valid or not any(combo) else Priority.MEDIUM

        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"DT: {combo_desc}",
                preconditions="System is ready for input",
                steps=[
                    _make_step(
                        "User is on the form", f"User provides: {combo_desc}", expected, step_format
                    )
                ],
                test_data=combo_desc,
                expected_result=expected,
                priority=priority,
                type=TestType.FUNCTIONAL if all_valid else TestType.NEGATIVE,
                istqb_technique=ISTQBTechnique.DECISION_TABLE,
                traceability=req.id,
            )
        )

    return cases


def state_transition(
    req: Requirement,
    start_id: int,
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Generate test cases using State Transition technique.

    Identifies states and transitions in the requirement.
    """
    cases: list[TestCase] = []
    states = _extract_states(req.text)

    if len(states) < 2:
        return cases

    # Test valid transitions between consecutive states
    for i in range(len(states) - 1):
        from_state = states[i]
        to_state = states[i + 1]
        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"ST Valid: {from_state} -> {to_state}",
                preconditions=f"System is in '{from_state}' state",
                steps=[
                    _make_step(
                        f"The system is in '{from_state}' state",
                        f"The trigger for transition to '{to_state}' occurs",
                        f"System transitions to '{to_state}' state",
                        step_format,
                    )
                ],
                test_data=f"Initial state: {from_state}, Action: trigger transition",
                expected_result=f"System is now in '{to_state}' state",
                priority=Priority.HIGH,
                type=TestType.FUNCTIONAL,
                istqb_technique=ISTQBTechnique.STATE_TRANSITION,
                traceability=req.id,
            )
        )

    # Test invalid transition (skip a state)
    if len(states) >= 3:
        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"ST Invalid: {states[0]} -> {states[-1]} (skip intermediate)",
                preconditions=f"System is in '{states[0]}' state",
                steps=[
                    _make_step(
                        f"The system is in '{states[0]}' state",
                        f"User attempts to jump directly to '{states[-1]}' state",
                        "System rejects the invalid transition",
                        step_format,
                    )
                ],
                test_data=f"Initial state: {states[0]}, Attempted: {states[-1]}",
                expected_result="Error: invalid state transition",
                priority=Priority.HIGH,
                type=TestType.NEGATIVE,
                istqb_technique=ISTQBTechnique.STATE_TRANSITION,
                traceability=req.id,
            )
        )

    return cases


def error_guessing(
    req: Requirement,
    start_id: int,
    step_format: StepFormat = StepFormat.GWT,
) -> list[TestCase]:
    """Generate test cases using Error Guessing technique.

    Tests common defect patterns: null, empty, special chars, SQL injection,
    extreme lengths, unicode, etc.
    """
    cases: list[TestCase] = []
    short = _short_title(req.text)

    error_patterns = [
        (
            "Null/empty input",
            "empty string / null",
            "Submit with null or empty value",
            "Validation error for missing required field",
            Priority.HIGH,
        ),
        (
            "Special characters",
            '<script>alert("xss")</script>',
            "Submit input with HTML/script tags",
            "Input is sanitized, no XSS execution",
            Priority.HIGH,
        ),
        (
            "SQL injection attempt",
            "'; DROP TABLE users; --",
            "Submit input with SQL injection pattern",
            "Input is sanitized, query is parameterized",
            Priority.HIGH,
        ),
        (
            "Extremely long input",
            "a" * 50 + "... (10000 chars)",
            "Submit input exceeding maximum expected length",
            "Validation error or graceful truncation",
            Priority.MEDIUM,
        ),
        (
            "Unicode characters",
            "Tes\u00f1\u00e9\u00fc\u00f6 \u4e16\u754c \u1f600",
            "Submit input with unicode and emoji characters",
            "System handles unicode correctly",
            Priority.MEDIUM,
        ),
        (
            "Whitespace-only input",
            "   \\t\\n  ",
            "Submit input with only whitespace characters",
            "Validation error: field cannot be blank",
            Priority.MEDIUM,
        ),
    ]

    for pattern_name, test_data, action, expected, priority in error_patterns:
        cases.append(
            TestCase(
                id=f"TC-{start_id + len(cases):03d}",
                title=f"EG: {pattern_name} for {short}",
                preconditions="System is ready to accept input",
                steps=[_make_step("User is on the input form", action, expected, step_format)],
                test_data=test_data,
                expected_result=expected,
                priority=priority,
                type=TestType.SECURITY
                if "injection" in pattern_name.lower() or "script" in test_data.lower()
                else TestType.NEGATIVE,
                istqb_technique=ISTQBTechnique.ERROR_GUESSING,
                traceability=req.id,
            )
        )

    return cases


def _make_step(
    given: str,
    when: str,
    then: str,
    step_format: StepFormat = StepFormat.GWT,
) -> Step:
    """Create a Step in the requested format."""
    if step_format == StepFormat.SER:
        return Step(step=f"{given}. {when}", expected=then)
    return Step(given=given, when=when, then=then)


# --- Helper functions ---


def _extract_numeric_constraints(text: str) -> list[tuple[str, int, int]]:
    """Extract numeric min/max constraints from text.

    Returns list of (field_name, min_value, max_value).
    """
    constraints: list[tuple[str, int, int]] = []

    # Pattern: "between X and Y"
    between = re.findall(
        r"(\w+(?:\s+\w+)?)\s+(?:between|entre)\s+(\d+)\s+(?:and|y)\s+(\d+)",
        text,
        re.IGNORECASE,
    )
    for field, min_v, max_v in between:
        constraints.append((field.strip(), int(min_v), int(max_v)))

    # Pattern: "minimum X ... maximum Y"
    range_pattern = re.findall(
        r"(?:minim(?:um|o))\s+(\d+).*?(?:maxim(?:um|o))\s+(\d+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    for min_v, max_v in range_pattern:
        constraints.append(("value", int(min_v), int(max_v)))

    return constraints


def _extract_conditions(text: str) -> list[str]:
    """Extract testable conditions from requirement text."""
    conditions: list[str] = []

    # Look for "must/should/shall" clauses — stop before next "and must/should/shall"
    must_clauses = re.findall(
        r"(?:must|should|shall|debe|tiene que)\s+(?:have|be|contain|include|accept|tener|ser|contener)"
        r"\s+(.+?)(?=\s+(?:and|y)\s+(?:must|should|shall|debe|tiene que)|[,.]|$)",
        text,
        re.IGNORECASE,
    )
    conditions.extend(c.strip() for c in must_clauses if c.strip())

    # Look for "and" separated conditions
    if not conditions:
        and_parts = re.split(r"\s+(?:and|y|,)\s+", text)
        conditions = [p.strip() for p in and_parts if len(p.strip()) > 5]

    return conditions


def _extract_states(text: str) -> list[str]:
    """Extract states or status values from text."""
    states: list[str] = []

    # Look for explicit state mentions
    state_pattern = re.findall(
        r"(?:state|status|estado)\s*[:\s]+\s*(\w+(?:\s+\w+)?)",
        text,
        re.IGNORECASE,
    )
    states.extend(state_pattern)

    # Look for flow patterns: "X -> Y -> Z" or "X → Y → Z"
    flow = re.findall(r"(\w+)\s*(?:->|→|=>|to)\s*(\w+)", text, re.IGNORECASE)
    for from_s, to_s in flow:
        if from_s not in states:
            states.append(from_s)
        if to_s not in states:
            states.append(to_s)

    # Look for common state words
    common_states = [
        "active",
        "inactive",
        "pending",
        "approved",
        "rejected",
        "locked",
        "unlocked",
        "enabled",
        "disabled",
        "draft",
        "published",
        "archived",
        "open",
        "closed",
        "in progress",
        "completed",
        "cancelled",
        "activo",
        "inactivo",
        "pendiente",
        "aprobado",
        "rechazado",
    ]
    for state in common_states:
        if state.lower() in text.lower() and state not in states:
            states.append(state)

    return states


def _generate_combinations(conditions: list[str]) -> list[tuple[bool, ...]]:
    """Generate all True/False combinations for conditions."""
    n = len(conditions)
    combos: list[tuple[bool, ...]] = []
    for i in range(2**n):
        combo = tuple(bool(i & (1 << j)) for j in range(n))
        combos.append(combo)
    return combos


def _short_title(text: str, max_len: int = 40) -> str:
    """Create a short title from requirement text."""
    clean = text.strip().replace("\n", " ")
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rsplit(" ", 1)[0] + "..."
