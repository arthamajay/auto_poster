"""Service orchestrating concurrent, fault-tolerant publishing across all configured platforms."""

import asyncio
from typing import List, Optional
import httpx

from app.config import Settings, get_settings
from app.platforms.base import BasePlatformClient
from app.platforms.telegraph_platform import TelegraphPlatform
from app.platforms.github_gist import GitHubGistPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.groq_llm_portal import GroqLLMPortalPlatform
from app.schemas import PlatformResult, PostingRequest, PostingResponse


class PostingService:
    """Manages internal platform selection and independent concurrent execution."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        platforms: Optional[List[BasePlatformClient]] = None,
    ) -> None:
        self.settings: Settings = settings if settings is not None else get_settings()
        self.platforms: List[BasePlatformClient] = platforms if platforms is not None else [
            TelegraphPlatform(self.settings),
            GitHubGistPlatform(self.settings),
            DevToPlatform(self.settings),
            BlueskyPlatform(self.settings),
            MastodonPlatform(self.settings),
            GroqLLMPortalPlatform(self.settings),
        ]

    async def publish_all(self, request: PostingRequest) -> PostingResponse:
        """Concurrently publish `request.message` to all platforms with full fault isolation."""
        cta_url = request.cta_url

        async with httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds, follow_redirects=True
        ) as client:
            tasks = [
                platform.publish_safe(
                    message=request.message, cta_url=cta_url, client=client
                )
                for platform in self.platforms
            ]
            results: List[PlatformResult] = list(await asyncio.gather(*tasks))

        overall_success = any(r.status == "success" for r in results)
        return PostingResponse(success=overall_success, results=results)
