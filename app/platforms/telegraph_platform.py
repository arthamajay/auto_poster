"""Telegraph (Telegra.ph) publishing portal integration.

Official API Documentation: https://telegra.ph/api
"""

import json
import httpx
from app.platforms.base import BasePlatformClient


class TelegraphPlatform(BasePlatformClient):
    """Publishes a formatted public page on Telegra.ph via its REST API."""

    platform_name = "Telegraph"
    API_BASE = "https://api.telegra.ph"

    async def _get_or_create_token(self, client: httpx.AsyncClient) -> str:
        if self.settings.telegraph_access_token:
            return self.settings.telegraph_access_token

        resp = await client.post(
            f"{self.API_BASE}/createAccount",
            data={
                "short_name": "AutoPoster",
                "author_name": self.settings.telegraph_author_name,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok") or "result" not in payload:
            raise ValueError(
                payload.get("error", "Failed to auto-provision Telegraph account token")
            )
        return payload["result"]["access_token"]

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        access_token = await self._get_or_create_token(client)
        content_nodes = [
            {"tag": "p", "children": [message]},
            {
                "tag": "p",
                "children": [
                    "Visit link: ",
                    {"tag": "a", "attrs": {"href": cta_url}, "children": [cta_url]},
                ],
            },
        ]
        response = await client.post(
            f"{self.API_BASE}/createPage",
            data={
                "access_token": access_token,
                "title": "Featured Update",
                "author_name": self.settings.telegraph_author_name,
                "content": json.dumps(content_nodes),
                "return_content": "false",
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok") or "result" not in data:
            raise ValueError(data.get("error", "Telegraph createPage API returned an error"))

        posted_url = data["result"].get("url")
        if not posted_url:
            raise ValueError("Telegraph response did not include a published URL")
        return posted_url
