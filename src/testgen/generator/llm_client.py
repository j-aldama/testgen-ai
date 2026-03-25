"""LLM client abstraction for structured test case generation."""

from __future__ import annotations

import abc
import json
import logging
import re
from typing import Any

from testgen.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BaseLLMClient(abc.ABC):
    """Abstract base for LLM clients that return structured JSON test cases."""

    @abc.abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        """Send a prompt to the LLM and return a list of test case dicts."""


class AnthropicLLMClient(BaseLLMClient):
    """Client that sends prompts to Claude via the Anthropic SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.anthropic_api_key:
            raise ValueError(
                "TESTGEN_ANTHROPIC_API_KEY environment variable is required. "
                "Set it in your .env file or environment."
            )
        import anthropic

        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        logger.info("Sending request to Anthropic (%s)", self._settings.anthropic_model)

        message = self._client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = message.content[0].text
        logger.debug("Raw LLM response length: %d chars", len(raw_text))

        return parse_json_response(raw_text)


class OpenAILLMClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs (OpenAI, Azure, Ollama, LM Studio, etc.)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.openai_api_key:
            raise ValueError(
                "TESTGEN_OPENAI_API_KEY environment variable is required. "
                "Set it in your .env file or environment."
            )
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install testgen[openai]"
            ) from exc

        client_kwargs: dict[str, Any] = {"api_key": self._settings.openai_api_key}
        if self._settings.openai_base_url:
            client_kwargs["base_url"] = self._settings.openai_base_url

        self._client = openai.OpenAI(**client_kwargs)

    def generate(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        logger.info("Sending request to OpenAI (%s)", self._settings.openai_model)

        response = self._client.chat.completions.create(
            model=self._settings.openai_model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.choices[0].message.content or ""
        logger.debug("Raw LLM response length: %d chars", len(raw_text))

        return parse_json_response(raw_text)


def create_llm_client(settings: Settings | None = None) -> BaseLLMClient:
    """Factory that creates the appropriate LLM client based on settings."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        return AnthropicLLMClient(settings)
    if provider == "openai":
        return OpenAILLMClient(settings)

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Supported providers: anthropic, openai"
    )


def parse_json_response(text: str) -> list[dict[str, Any]]:
    """Parse LLM response text into a list of dictionaries.

    Handles responses wrapped in markdown code blocks or with extra text.
    """
    # Strip markdown code blocks if present
    cleaned = text.strip()
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    if code_block:
        cleaned = code_block.group(1).strip()

    # Try parsing as JSON array directly
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "test_cases" in result:
            return result["test_cases"]
        return [result]
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the text
    array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if array_match:
        try:
            result = json.loads(array_match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse LLM response as JSON: %s...", cleaned[:200])
    raise ValueError("LLM response could not be parsed as valid JSON test cases.")


# Backward-compatible alias
LLMClient = AnthropicLLMClient
_parse_json_response = parse_json_response
