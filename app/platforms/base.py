"""Abstract base class and helper utilities for third-party platform integrations."""

from abc import ABC, abstractmethod
from datetime import datetime
import httpx
from app.config import Settings
from app.schemas import PlatformResult


class BasePlatformClient(ABC):
    """Base contract for all third-party publishing platforms."""

    platform_name: str = "Base Platform"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def _publish(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> str:
        """Publish the message via the platform's REST API and return the public post URL.

        Raises an Exception with a descriptive message if authentication or publishing fails.
        """
        raise NotImplementedError

    async def publish_safe(
        self, message: str, cta_url: str, client: httpx.AsyncClient
    ) -> PlatformResult:
        """Execute `_publish` with full error isolation and standardized result formatting."""
        try:
            posted_url = await self._publish(message=message, cta_url=cta_url, client=client)
            now = datetime.now()
            return PlatformResult(
                platform=self.platform_name,
                status="success",
                posted_url=posted_url,
                public_access=True,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
                error=None,
            )
        except httpx.TimeoutException:
            return self._failure("Request timed out while connecting to platform API")
        except httpx.ConnectError as exc:
            return self._failure(f"Connection error — platform may be unreachable from this network: {exc}")
        except httpx.HTTPStatusError as exc:
            return self._failure(
                f"HTTP {exc.response.status_code}: {self._extract_api_error(exc.response)}"
            )
        except Exception as exc:
            return self._failure(str(exc))

    def _failure(self, error_message: str) -> PlatformResult:
        """Build a standardized failed PlatformResult."""
        return PlatformResult(
            platform=self.platform_name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error_message,
        )

    @staticmethod
    def _extract_api_error(response: httpx.Response) -> str:
        """Extract a concise human-readable error message from an HTTP error response."""
        try:
            data = response.json()
            if isinstance(data, dict):
                for key in ("error", "message", "detail", "error_description"):
                    if key in data and data[key]:
                        return str(data[key])
        except Exception:
            pass
        text = response.text.strip()
        return text[:160] if text else response.reason_phrase
