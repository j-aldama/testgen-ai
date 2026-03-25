"""Tests for the FastAPI web application."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    Priority,
    Requirement,
    Step,
    TestCase,
    TestType,
)
from testgen.web.app import app, _sessions


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def populated_session(sample_generation_result: GenerationResult) -> str:
    """Add a result to the session store and return the session_id."""
    session_id = sample_generation_result.session_id
    _sessions[session_id] = sample_generation_result
    yield session_id
    _sessions.pop(session_id, None)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


class TestIndexPage:
    """Tests for the main page."""

    def test_index_returns_html(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_form(self, client: TestClient) -> None:
        response = client.get("/")
        content = response.text
        assert "requirements_text" in content
        assert "Generate Test Cases" in content

    def test_index_has_technique_checkboxes(self, client: TestClient) -> None:
        response = client.get("/")
        content = response.text
        assert "Equivalence Partitioning" in content
        assert "Boundary Value Analysis" in content
        assert "Decision Table" in content


class TestResultsEndpoint:
    """Tests for viewing results."""

    def test_results_found(
        self, client: TestClient, populated_session: str
    ) -> None:
        response = client.get(f"/results/{populated_session}")
        assert response.status_code == 200
        assert "TC-001" in response.text

    def test_results_not_found(self, client: TestClient) -> None:
        response = client.get("/results/nonexistent")
        assert response.status_code == 404


class TestDownloadEndpoints:
    """Tests for file download endpoints."""

    def test_download_md(
        self, client: TestClient, populated_session: str
    ) -> None:
        response = client.get(f"/download/{populated_session}/md")
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

    def test_download_json(
        self, client: TestClient, populated_session: str
    ) -> None:
        response = client.get(f"/download/{populated_session}/json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert "test_cases" in data

    def test_download_xlsx(
        self, client: TestClient, populated_session: str
    ) -> None:
        response = client.get(f"/download/{populated_session}/xlsx")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]

    def test_download_unknown_format(
        self, client: TestClient, populated_session: str
    ) -> None:
        response = client.get(f"/download/{populated_session}/csv")
        assert response.status_code == 400

    def test_download_session_not_found(self, client: TestClient) -> None:
        response = client.get("/download/nonexistent/md")
        assert response.status_code == 404


class TestGenerateEndpoint:
    """Tests for the generate endpoint (mocked LLM)."""

    @patch("testgen.web.app.create_llm_client")
    def test_generate_returns_results(
        self, mock_create_llm: MagicMock, client: TestClient
    ) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = [
            {
                "id": "TC-001",
                "title": "Test login with valid credentials",
                "preconditions": "User exists",
                "steps": [{"given": "User on login", "when": "Enter creds", "then": "Logged in"}],
                "test_data": "email=test@test.com",
                "expected_result": "Login success",
                "priority": "High",
                "type": "Functional",
                "istqb_technique": "Equivalence Partitioning",
                "traceability": "REQ-001",
            }
        ]
        mock_create_llm.return_value = mock_llm

        response = client.post(
            "/generate",
            data={
                "requirements_text": "The user must be able to log in with email and password.",
            },
        )
        assert response.status_code == 200
        assert "TC-001" in response.text

    def test_generate_empty_text_fails(self, client: TestClient) -> None:
        response = client.post(
            "/generate",
            data={"requirements_text": ""},
        )
        assert response.status_code == 400 or response.status_code == 422
