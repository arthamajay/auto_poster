"""GitHub Gist REST API integration.

Official API Documentation: https://docs.github.com/en/rest/gists/gists
"""

import httpx
from app.platforms.base import BasePlatformClient


class GitHubGistPlatform(BasePlatformClient):
    """Publishes a public Markdown Gist on GitHub."""

    platform_name = "GitHub Gist"
    API_URL = "https://api.github.com/gists"

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        if not self.settings.github_token or self.settings.github_token.startswith("your_"):
            raise ValueError(
                "Authentication failed: GITHUB_TOKEN is not configured in environment"
            )

        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        markdown_body = (
            f"# Announcement\n\n{message}\n\n"
            f"CTA Link: [{cta_url}]({cta_url})\n"
        )
        payload = {
            "description": message[:120],
            "public": True,
            "files": {
                "announcement.md": {
                    "content": markdown_body,
                }
            },
        }

        response = await client.post(self.API_URL, headers=headers, json=payload)
        if response.status_code in (401, 403):
            raise ValueError("Authentication failed: Invalid or unauthorized GITHUB_TOKEN")
        response.raise_for_status()

        data = response.json()
        posted_url = data.get("html_url")
        if not posted_url:
            raise ValueError("GitHub Gist API response missing 'html_url'")
        return posted_url
