"""Main orchestrator for test case generation."""

from __future__ import annotations

import logging
from typing import Any

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    Priority,
    Requirement,
    Step,
    StepFormat,
    TestCase,
    TestType,
)
from testgen.generator.llm_client import BaseLLMClient
from testgen.generator.prompts import build_system_prompt, build_user_prompt
from testgen.generator.techniques import apply_techniques

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """Orchestrates the full test case generation pipeline.

    1. Takes parsed requirements
    2. Sends them to the LLM for initial generation
    3. Applies ISTQB techniques for additional coverage
    4. Returns structured GenerationResult
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self._llm_client = llm_client

    def generate(
        self,
        requirements: list[Requirement],
        techniques: list[ISTQBTechnique] | None = None,
        priorities: list[str] | None = None,
        types: list[str] | None = None,
        step_format: StepFormat = StepFormat.GWT,
        tc_per_req: int = 5,
    ) -> GenerationResult:
        """Generate test cases from requirements.

        Args:
            requirements: List of parsed requirements.
            techniques: Optional list of ISTQB techniques to apply.
            priorities: Optional filter for priority levels.
            types: Optional filter for test types.

        Returns:
            GenerationResult containing all generated test cases.
        """
        if not requirements:
            raise ValueError("No requirements provided for test case generation.")

        result = GenerationResult(requirements=requirements, step_format=step_format.value)

        technique_names = (
            [t.value for t in techniques] if techniques else None
        )
        priority_names = priorities
        type_names = types

        # Step 1: LLM-based generation
        req_dicts = [r.to_dict() for r in requirements]
        user_prompt = build_user_prompt(
            req_dicts,
            techniques=technique_names,
            priorities=priority_names,
            types=type_names,
        )

        if self._llm_client is None:
            raise ValueError(
                "LLM client not configured. Set TESTGEN_LLM_PROVIDER and the corresponding API key."
            )

        system_prompt = build_system_prompt(step_format, tc_per_req=tc_per_req)
        raw_cases = self._llm_client.generate(system_prompt, user_prompt)
        logger.info("LLM returned %d raw test cases", len(raw_cases))

        # Step 2: Parse raw LLM output into TestCase objects
        test_cases = _parse_raw_test_cases(raw_cases, requirements)
        result.test_cases.extend(test_cases)

        # Step 3: Apply ISTQB techniques for additional coverage
        if techniques:
            additional = apply_techniques(
                requirements, techniques, result.test_cases, step_format
            )
            result.test_cases.extend(additional)
            logger.info(
                "Techniques added %d additional test cases", len(additional)
            )

        # Step 4: Re-number all test cases sequentially
        for i, tc in enumerate(result.test_cases, 1):
            tc.id = f"TC-{i:03d}"

        logger.info("Total test cases generated: %d", len(result.test_cases))
        return result


def _parse_raw_test_cases(
    raw_cases: list[dict[str, Any]],
    requirements: list[Requirement],
) -> list[TestCase]:
    """Convert raw LLM dict output into validated TestCase objects."""
    test_cases: list[TestCase] = []
    req_ids = {r.id for r in requirements}
    default_req_id = requirements[0].id if requirements else "REQ-001"

    for i, raw in enumerate(raw_cases, 1):
        try:
            tc = _build_test_case(raw, i, req_ids, default_req_id)
            test_cases.append(tc)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed test case #%d: %s", i, exc)
            continue

    return test_cases


def _build_test_case(
    raw: dict[str, Any],
    index: int,
    valid_req_ids: set[str],
    default_req_id: str,
) -> TestCase:
    """Build a single TestCase from raw LLM output with validation."""
    tc_id = raw.get("id", f"TC-{index:03d}")

    # Parse steps
    raw_steps = raw.get("steps", [])
    steps: list[Step] = []
    if isinstance(raw_steps, list):
        for step_data in raw_steps:
            if isinstance(step_data, dict):
                steps.append(
                    Step(
                        given=step_data.get("given", ""),
                        when=step_data.get("when", ""),
                        then=step_data.get("then", ""),
                        step=step_data.get("step", ""),
                        expected=step_data.get("expected", ""),
                    )
                )
            elif isinstance(step_data, str):
                steps.append(Step(given="", when=step_data, then=""))

    if not steps:
        steps = [Step(given="N/A", when="N/A", then="N/A")]

    # Parse priority
    priority = _parse_enum(raw.get("priority", "Medium"), Priority, Priority.MEDIUM)

    # Parse type
    test_type = _parse_enum(raw.get("type", "Functional"), TestType, TestType.FUNCTIONAL)

    # Parse technique
    technique = _parse_enum(
        raw.get("istqb_technique", "Equivalence Partitioning"),
        ISTQBTechnique,
        ISTQBTechnique.EQUIVALENCE_PARTITIONING,
    )

    # Validate traceability
    traceability = raw.get("traceability", default_req_id)
    if traceability not in valid_req_ids:
        traceability = default_req_id

    return TestCase(
        id=tc_id,
        title=raw.get("title", f"Test Case {index}"),
        preconditions=raw.get("preconditions", "N/A"),
        steps=steps,
        test_data=raw.get("test_data", "N/A"),
        expected_result=raw.get("expected_result", "N/A"),
        priority=priority,
        type=test_type,
        istqb_technique=technique,
        traceability=traceability,
    )


def _parse_enum(value: str, enum_class: type, default: Any) -> Any:
    """Parse a string value into an enum, returning default on failure."""
    if isinstance(value, str):
        for member in enum_class:
            if member.value.lower() == value.lower():
                return member
    return default
