"""Bluesky (AT Protocol) XRPC API integration.

Official API Documentation: https://bsky.network/docs/bluesky-api/creating-a-post/
"""

from datetime import datetime, timezone
import httpx
from app.platforms.base import BasePlatformClient


class BlueskyPlatform(BasePlatformClient):
    """Publishes a public post with rich-text link facets to Bluesky via AT Protocol."""

    platform_name = "Bluesky"

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        handle = self.settings.bluesky_handle
        password = self.settings.bluesky_app_password
        if (
            not handle
            or not password
            or handle.startswith("your_")
            or password.startswith("your_")
        ):
            raise ValueError(
                "Authentication failed: BLUESKY_HANDLE or BLUESKY_APP_PASSWORD is not configured"
            )

        base_url = self.settings.bluesky_service_url
        session_resp = await client.post(
            f"{base_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        if session_resp.status_code in (400, 401, 403):
            raise ValueError("Authentication failed: Invalid Bluesky handle or app password")
        session_resp.raise_for_status()

        session_data = session_resp.json()
        access_jwt = session_data["accessJwt"]
        did = session_data["did"]
        resolved_handle = session_data.get("handle", handle)

        # Compute UTF-8 byte offsets so the CTA link is clickable on Bluesky
        facets = []
        utf8_message = message.encode("utf-8")
        utf8_url = cta_url.encode("utf-8")
        byte_start = utf8_message.find(utf8_url)
        if byte_start != -1:
            facets.append(
                {
                    "index": {
                        "byteStart": byte_start,
                        "byteEnd": byte_start + len(utf8_url),
                    },
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": cta_url,
                        }
                    ],
                }
            )

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if facets:
            record["facets"] = facets

        post_resp = await client.post(
            f"{base_url}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        post_resp.raise_for_status()
        post_data = post_resp.json()
        uri = post_data.get("uri", "")
        rkey = uri.rsplit("/", 1)[-1] if "/" in uri else ""
        if not rkey:
            raise ValueError("Bluesky createRecord response did not return a valid record URI")

        return f"https://bsky.app/profile/{resolved_handle}/post/{rkey}"
