"""Dev.to (Forem V1) API integration.

Official API Documentation: https://developers.forem.com/api/v1
"""

import httpx
from app.platforms.base import BasePlatformClient


class DevToPlatform(BasePlatformClient):
    """Publishes a public post on Dev.to via the Forem v1 Articles endpoint."""

    platform_name = "Dev.to"
    API_URL = "https://dev.to/api/articles"

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        if not self.settings.devto_api_key or self.settings.devto_api_key.startswith("your_"):
            raise ValueError(
                "Authentication failed: DEVTO_API_KEY is not configured in environment"
            )

        headers = {
            "api-key": self.settings.devto_api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        }
        headline = message.replace(cta_url, "").strip().rstrip(".,!?;:-")
        title = (headline[:65] or "Platform Update") + " — Official Link"
        body_markdown = (
            f"{message}\n\n"
            f"### Explore Further\n"
            f"Visit [{cta_url}]({cta_url}) to learn more."
        )
        payload = {
            "article": {
                "title": title,
                "published": True,
                "body_markdown": body_markdown,
                "tags": ["webdev", "productivity", "announcement"],
            }
        }

        response = await client.post(self.API_URL, headers=headers, json=payload)
        if response.status_code in (401, 403):
            raise ValueError("Authentication failed: Invalid DEVTO_API_KEY")
        response.raise_for_status()

        data = response.json()
        posted_url = data.get("url")
        if not posted_url:
            raise ValueError("Dev.to API response did not contain article 'url'")
        return posted_url
