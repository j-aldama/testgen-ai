"""System and user prompts for the LLM-based test case generator."""

from __future__ import annotations

from testgen.config import StepFormat

_STEPS_GWT = """\
  "steps": [
    {
      "given": "Initial context/state",
      "when": "Action performed",
      "then": "Expected outcome"
    }
  ],"""

_STEPS_SER = """\
  "steps": [
    {
      "step": "Description of action to perform",
      "expected": "Expected result of this step"
    }
  ],"""

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert SDET (Software Development Engineer in Test) and ISTQB-certified test designer. \
Your task is to generate comprehensive, structured test cases from software requirements.

You MUST respond with ONLY valid JSON. No markdown, no explanations, no code blocks — just raw JSON.

## Output Format

Return a JSON array of test case objects. Each test case MUST have these fields:
{{
  "id": "TC-XXX",
  "title": "Descriptive title of what is being tested",
  "preconditions": "What must be true before executing this test",
{steps_block}
  "test_data": "Specific input values to use",
  "expected_result": "Clear description of expected behavior",
  "priority": "High|Medium|Low",
  "type": "Functional|Negative|Boundary|Security|Performance|Accessibility",
  "istqb_technique": "Equivalence Partitioning|Boundary Value Analysis|Decision Table|\
State Transition|Error Guessing",
  "traceability": "REQ-XXX"
}}

## ISTQB Techniques Guide

### Equivalence Partitioning (EP)
Divide input domains into equivalence classes. Generate ONE test per class.
- Valid class: inputs within acceptable range
- Invalid class: inputs outside acceptable range
Example: For age field (18-65): valid={{25}}, invalid_low={{10}}, invalid_high={{80}}, \
invalid_type={{"abc"}}

### Boundary Value Analysis (BVA)
Test at exact boundary values: min-1, min, min+1, max-1, max, max+1.
Example: For password length 8-20: test with 7, 8, 9, 19, 20, 21 characters

### Decision Table
Map combinations of conditions to expected actions.
Example: For login with valid/invalid email × valid/invalid password = 4 combinations

### State Transition
Test transitions between system states and invalid transitions.
Example: Account states: Active → Locked (3 failed attempts) → Active (admin unlock)

### Error Guessing
Based on common defect patterns: null/empty inputs, special characters, SQL injection attempts, \
extreme values, concurrent operations, unicode, whitespace-only inputs.

## Rules
1. Generate 3-8 test cases per requirement (cover happy path + edge cases + negative)
2. Always include at least one negative test case
3. Always include at least one boundary test case when applicable
4. Test data must be CONCRETE (actual values, not placeholders)
5. Steps must be actionable and verifiable
6. Traceability must reference the source requirement ID
7. Use diverse ISTQB techniques across test cases
8. Prioritize: security and data integrity = High, core functionality = High, \
edge cases = Medium, UI/cosmetic = Low
9. You MUST generate all text content (titles, preconditions, steps, expected results, \
test data descriptions) in the SAME LANGUAGE as the input requirements. \
If requirements are in Spanish, respond in Spanish. If in English, respond in English. \
Field keys (id, given, when, then, step, expected, priority, type, etc.) must remain in English."""


def build_system_prompt(
    step_format: StepFormat = StepFormat.GWT,
    tc_per_req: int = 5,
) -> str:
    """Build the system prompt with the appropriate step format and count."""
    steps_block = _STEPS_GWT if step_format == StepFormat.GWT else _STEPS_SER
    prompt = _SYSTEM_PROMPT_TEMPLATE.format(steps_block=steps_block)
    # Replace the hardcoded range with the user's choice
    prompt = prompt.replace(
        "Generate 3-8 test cases per requirement",
        f"Generate approximately {tc_per_req} test cases per requirement",
    )
    return prompt


# Backward-compatible alias
SYSTEM_PROMPT = build_system_prompt(StepFormat.GWT)


def build_user_prompt(
    requirements: list[dict[str, str]],
    techniques: list[str] | None = None,
    priorities: list[str] | None = None,
    types: list[str] | None = None,
) -> str:
    """Build the user prompt with requirements and optional filters."""
    parts: list[str] = []

    parts.append("Generate test cases for the following requirements:\n")
    for req in requirements:
        parts.append(f"**{req['id']}**: {req['text']}\n")

    if techniques:
        parts.append(f"\nFocus on these ISTQB techniques: {', '.join(techniques)}")

    if priorities:
        parts.append(f"\nGenerate only {', '.join(priorities)} priority test cases.")

    if types:
        parts.append(f"\nGenerate only these test types: {', '.join(types)}")

    parts.append(
        "\n\nIMPORTANT: Write ALL text content (titles, preconditions, steps, "
        "test data, expected results) in the SAME LANGUAGE as the requirements above. "
        "Only JSON keys stay in English."
        "\n\nReturn ONLY a JSON array of test case objects. "
        "No markdown code blocks, no explanations."
    )

    return "\n".join(parts)


TECHNIQUE_SPECIFIC_PROMPTS: dict[str, str] = {
    "Equivalence Partitioning": (
        "Apply Equivalence Partitioning: identify valid and invalid equivalence classes "
        "for each input. Generate one test per class. Include at least one valid class "
        "and two invalid classes (wrong type, out of range)."
    ),
    "Boundary Value Analysis": (
        "Apply Boundary Value Analysis: for each numeric or length constraint, "
        "test at min-1, min, min+1, max-1, max, max+1. Include exact boundary values "
        "in test_data."
    ),
    "Decision Table": (
        "Apply Decision Table testing: identify all conditions and their True/False "
        "combinations. Generate one test per combination row. Cover all feasible "
        "condition combinations."
    ),
    "State Transition": (
        "Apply State Transition testing: identify all system states and valid/invalid "
        "transitions. Test each valid transition and at least one invalid transition. "
        "Include the state diagram flow in steps."
    ),
    "Error Guessing": (
        "Apply Error Guessing: test with null, empty string, special characters "
        "(< > ' \" & ; --), extremely long inputs (10000+ chars), SQL injection "
        "patterns, unicode characters, whitespace-only inputs, and zero/negative "
        "numbers where applicable."
    ),
}
