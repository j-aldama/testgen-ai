"""Configuration and data models for TestGen."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings


class Priority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TestType(StrEnum):
    FUNCTIONAL = "Functional"
    NEGATIVE = "Negative"
    BOUNDARY = "Boundary"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    ACCESSIBILITY = "Accessibility"


class ISTQBTechnique(StrEnum):
    EQUIVALENCE_PARTITIONING = "Equivalence Partitioning"
    BOUNDARY_VALUE_ANALYSIS = "Boundary Value Analysis"
    DECISION_TABLE = "Decision Table"
    STATE_TRANSITION = "State Transition"
    ERROR_GUESSING = "Error Guessing"


class StepFormat(StrEnum):
    GWT = "given_when_then"
    SER = "step_expected"


STEP_FORMAT_MAP: dict[str, StepFormat] = {
    "gwt": StepFormat.GWT,
    "given_when_then": StepFormat.GWT,
    "ser": StepFormat.SER,
    "step_expected": StepFormat.SER,
}


TECHNIQUE_SHORT_MAP: dict[str, ISTQBTechnique] = {
    "ep": ISTQBTechnique.EQUIVALENCE_PARTITIONING,
    "bva": ISTQBTechnique.BOUNDARY_VALUE_ANALYSIS,
    "dt": ISTQBTechnique.DECISION_TABLE,
    "st": ISTQBTechnique.STATE_TRANSITION,
    "eg": ISTQBTechnique.ERROR_GUESSING,
}


@dataclass
class Step:
    """A single test step. Supports GWT and Step/Expected formats."""

    given: str = ""
    when: str = ""
    then: str = ""
    step: str = ""
    expected: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "given": self.given, "when": self.when, "then": self.then,
            "step": self.step, "expected": self.expected,
        }


@dataclass
class TestCase:
    """A complete test case with all ISTQB-aligned fields."""

    id: str
    title: str
    preconditions: str
    steps: list[Step]
    test_data: str
    expected_result: str
    priority: Priority
    type: TestType
    istqb_technique: ISTQBTechnique
    traceability: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "preconditions": self.preconditions,
            "steps": [s.to_dict() for s in self.steps],
            "test_data": self.test_data,
            "expected_result": self.expected_result,
            "priority": self.priority.value,
            "type": self.type.value,
            "istqb_technique": self.istqb_technique.value,
            "traceability": self.traceability,
        }


@dataclass
class Requirement:
    """A parsed requirement from user input."""

    id: str
    text: str
    source: str = "user_input"

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "text": self.text, "source": self.source}


@dataclass
class GenerationResult:
    """Result of a test case generation run."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    requirements: list[Requirement] = field(default_factory=list)
    test_cases: list[TestCase] = field(default_factory=list)
    step_format: str = "given_when_then"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "requirements": [r.to_dict() for r in self.requirements],
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }

    @property
    def summary(self) -> dict[str, int]:
        by_priority = {}
        by_type = {}
        by_technique = {}
        for tc in self.test_cases:
            by_priority[tc.priority.value] = by_priority.get(tc.priority.value, 0) + 1
            by_type[tc.type.value] = by_type.get(tc.type.value, 0) + 1
            by_technique[tc.istqb_technique.value] = (
                by_technique.get(tc.istqb_technique.value, 0) + 1
            )
        return {
            "total": len(self.test_cases),
            "requirements_count": len(self.requirements),
            "by_priority": by_priority,
            "by_type": by_type,
            "by_technique": by_technique,
        }


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Provider selection: "anthropic" or "openai"
    llm_provider: str = "anthropic"

    # Anthropic settings
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenAI-compatible settings (OpenAI, Azure, Ollama, LM Studio, etc.)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = ""

    # Shared LLM settings
    max_tokens: int = 8192
    temperature: float = 0.3

    # Web server
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    output_dir: str = "./output"
    log_level: str = "INFO"

    model_config = {"env_prefix": "TESTGEN_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()


def get_output_dir() -> Path:
    settings = get_settings()
    path = Path(settings.output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
