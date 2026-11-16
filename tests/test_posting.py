"""Unit and integration tests for input validation, multi-platform posting, and fault tolerance."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_posting_service, get_settings
from app.platforms.base import BasePlatformClient
from app.services.posting_service import PostingService


class MockSuccessPlatform(BasePlatformClient):
    def __init__(self, settings: Settings, name: str, base_url: str) -> None:
        super().__init__(settings)
        self.platform_name = name
        self.base_url = base_url

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        return f"{self.base_url}/post/101"


class MockFailurePlatform(BasePlatformClient):
    def __init__(self, settings: Settings, name: str, error_msg: str) -> None:
        super().__init__(settings)
        self.platform_name = name
        self.error_msg = error_msg

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        raise ValueError(self.error_msg)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_validation_rejects_message_exceeding_200_chars(client: TestClient) -> None:
    long_text = "A" * 185 + " https://example.com"
    assert len(long_text) > 200
    response = client.post("/posting", json={"message": long_text})
    assert response.status_code == 422
    assert "200 characters" in str(response.json())


def test_validation_rejects_missing_cta_link(client: TestClient) -> None:
    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform and grow visibility."},
    )
    assert response.status_code == 422
    assert "exactly one valid CTA link" in str(response.json())


def test_validation_rejects_multiple_cta_links(client: TestClient) -> None:
    response = client.post(
        "/posting",
        json={
            "message": "Visit https://example.com and also check https://second-link.org today!"
        },
    )
    assert response.status_code == 422
    assert "exactly one CTA link" in str(response.json())


def test_validation_rejects_invalid_domain_url(client: TestClient) -> None:
    response = client.post(
        "/posting",
        json={"message": "Check out our platform at https://invalid_domain_without_tld"},
    )
    assert response.status_code == 422


def test_validation_rejects_url_only_without_text(client: TestClient) -> None:
    response = client.post("/posting", json={"message": "https://example.com"})
    assert response.status_code == 422
    assert "descriptive text" in str(response.json())


def test_validation_rejects_external_platform_override(client: TestClient) -> None:
    """Platform selection must be handled internally by the application."""
    response = client.post(
        "/posting",
        json={
            "message": "Check out our latest business platform https://example.com",
            "platforms": ["Telegraph"],
        },
    )
    assert response.status_code == 422


def test_partial_failure_fault_isolation() -> None:
    """If one or more platforms fail, remaining platforms must still succeed independently."""
    settings = Settings()
    mock_platforms = [
        MockSuccessPlatform(settings, "Telegraph", "https://telegra.ph"),
        MockSuccessPlatform(settings, "GitHub Gist", "https://gist.github.com"),
        MockFailurePlatform(settings, "Dev.to", "Authentication failed"),
        MockSuccessPlatform(settings, "Bluesky", "https://bsky.app"),
        MockFailurePlatform(settings, "Mastodon", "Authentication failed"),
        MockSuccessPlatform(settings, "Groq LLM Portal", "https://telegra.ph/groq"),
    ]
    app.dependency_overrides[get_posting_service] = lambda settings=None: PostingService(
        settings=settings or Settings(), platforms=mock_platforms
    )
    app.dependency_overrides[get_settings] = lambda: Settings()

    try:
        test_client = TestClient(app)
        response = test_client.post(
            "/posting",
            json={
                "message": "Check out our latest business platform and grow your online visibility. https://example.com"
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["results"]) == 6

        by_name = {item["platform"]: item for item in body["results"]}
        assert by_name["Telegraph"]["status"] == "success"
        assert by_name["Telegraph"]["posted_url"] == "https://telegra.ph/post/101"
        assert by_name["Telegraph"]["public_access"] is True
        assert by_name["Telegraph"]["date"] is not None
        assert by_name["Telegraph"]["time"] is not None
        assert by_name["Telegraph"]["error"] is None

        assert by_name["Dev.to"]["status"] == "failed"
        assert by_name["Dev.to"]["posted_url"] is None
        assert by_name["Dev.to"]["public_access"] is False
        assert by_name["Dev.to"]["date"] is None
        assert by_name["Dev.to"]["time"] is None
        assert by_name["Dev.to"]["error"] == "Authentication failed"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
