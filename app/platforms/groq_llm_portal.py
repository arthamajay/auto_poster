"""Groq LLM Platform API integration with public Telegraph AI Showcase publishing.

Official API Documentation:
- Groq Chat Completions API: https://console.groq.com/docs/api-reference
- Telegraph API: https://telegra.ph/api
"""

import json
import httpx
from app.platforms.base import BasePlatformClient


class GroqLLMPortalPlatform(BasePlatformClient):
    """Synthesizes an AI-enhanced promotional brief via Groq LLM and publishes a public showcase page."""

    platform_name = "Groq LLM Portal"
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    TELEGRAPH_BASE = "https://api.telegra.ph"

    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        if not self.settings.groq_api_key or self.settings.groq_api_key.startswith("your_"):
            raise ValueError(
                "Authentication failed: GROQ_API_KEY is not configured in environment"
            )

        # Step 1: Call Groq LLM Chat Completions API
        groq_headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        groq_payload = {
            "model": self.settings.groq_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a concise marketing assistant. Summarize and highlight the value "
                        "of the user's announcement in 2 short sentences while preserving the CTA link."
                    ),
                },
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
            "max_tokens": 150,
        }

        groq_resp = await client.post(
            self.GROQ_URL, headers=groq_headers, json=groq_payload
        )
        if groq_resp.status_code in (401, 403):
            raise ValueError("Authentication failed: Invalid GROQ_API_KEY")
        groq_resp.raise_for_status()

        groq_data = groq_resp.json()
        ai_summary = (
            groq_data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not ai_summary:
            raise ValueError("Groq LLM API returned an empty completion")

        # Step 2: Publish the original message + Groq LLM summary to a public URL
        token = self.settings.telegraph_access_token
        if not token:
            acct_resp = await client.post(
                f"{self.TELEGRAPH_BASE}/createAccount",
                data={"short_name": "GroqAgent", "author_name": "Groq LLM Publisher"},
            )
            acct_resp.raise_for_status()
            acct_data = acct_resp.json()
            if not acct_data.get("ok") or "result" not in acct_data:
                raise ValueError(
                    acct_data.get("error", "Failed to auto-provision Telegraph account for Groq showcase")
                )
            token = acct_data["result"]["access_token"]

        content_nodes = [
            {"tag": "h4", "children": ["Original Message"]},
            {"tag": "p", "children": [message]},
            {"tag": "h4", "children": [f"Groq LLM ({self.settings.groq_model}) Spotlight"]},
            {"tag": "p", "children": [ai_summary]},
            {
                "tag": "p",
                "children": [
                    "CTA Link: ",
                    {"tag": "a", "attrs": {"href": cta_url}, "children": [cta_url]},
                ],
            },
        ]
        page_resp = await client.post(
            f"{self.TELEGRAPH_BASE}/createPage",
            data={
                "access_token": token,
                "title": "Groq LLM Syndicated Post",
                "author_name": "Groq LLM Publisher",
                "content": json.dumps(content_nodes),
            },
        )
        page_resp.raise_for_status()
        page_data = page_resp.json()
        if not page_data.get("ok") or "result" not in page_data:
            raise ValueError("Failed to publish Groq LLM output page")
        return page_data["result"]["url"]
