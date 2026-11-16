"""Mastodon REST API v1 integration.

Official API Documentation: https://docs.joinmastodon.org/methods/statuses/
"""

import httpx
from app.platforms.base import BasePlatformClient


class MastodonPlatform(BasePlatformClient):
    """Publishes a public status update on a Mastodon instance."""

    platform_name = "Mastodon"

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        token = self.settings.mastodon_access_token
        if not token or token.startswith("your_"):
            raise ValueError(
                "Authentication failed: MASTODON_ACCESS_TOKEN is not configured in environment"
            )

        endpoint = f"{self.settings.mastodon_instance_url}/api/v1/statuses"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "status": message,
            "visibility": "public",
        }

        response = await client.post(endpoint, headers=headers, json=payload)
        if response.status_code in (401, 403):
            raise ValueError("Authentication failed: Invalid MASTODON_ACCESS_TOKEN")
        response.raise_for_status()

        data = response.json()
        posted_url = data.get("url") or data.get("uri")
        if not posted_url:
            raise ValueError("Mastodon API response missing public status 'url'")
        return posted_url
