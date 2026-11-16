"""Pydantic request and response schemas with strict message and CTA URL validation (Pydantic v1 & v2 compatible)."""

import re
from typing import List, Literal, Optional
from urllib.parse import urlparse
import pydantic
from pydantic import BaseModel, Field

PYDANTIC_V2 = int(getattr(pydantic, "__version__", "1.0.0").split(".")[0]) >= 2
if PYDANTIC_V2:
    from pydantic import ConfigDict, field_validator
else:
    from pydantic import Extra, validator

# Regex matching URLs or URL-like tokens in the message
URL_CANDIDATE_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
TRAILING_PUNCTUATION = '.,!?;:)]}\'"'


def extract_and_validate_single_cta_url(message: str) -> str:
    """Validate that `message` is <= 200 chars and contains exactly one valid HTTP/HTTPS URL."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty.")

    if len(message) > 200:
        raise ValueError(
            f"Message must not exceed 200 characters (received {len(message)} characters)."
        )

    raw_matches = URL_CANDIDATE_PATTERN.findall(message)
    cleaned_urls = [match.rstrip(TRAILING_PUNCTUATION) for match in raw_matches]

    if len(cleaned_urls) == 0:
        raise ValueError(
            "Message must include exactly one valid CTA link (starting with http:// or https://)."
        )
    if len(cleaned_urls) > 1:
        raise ValueError(
            f"Message must contain exactly one CTA link, but {len(cleaned_urls)} links were found."
        )

    cta_url = cleaned_urls[0]
    parsed = urlparse(cta_url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("CTA link must use http:// or https:// protocol.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid CTA URL hostname in '{cta_url}'.")

    # Validate domain structure (must be localhost or contain a valid dot-separated TLD)
    if hostname.lower() != "localhost":
        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
        )
        if not domain_regex.match(hostname):
            raise ValueError(f"Invalid domain name in CTA link: '{cta_url}'.")

    # Ensure there is also promotional/descriptive message text alongside the URL
    non_url_text = message.replace(cta_url, "").strip()
    if not non_url_text:
        raise ValueError(
            "Message must include descriptive text in addition to the CTA link."
        )

    return cta_url


class PostingRequest(BaseModel):
    """Input payload for POST /posting."""

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="forbid")
    else:
        class Config:
            extra = Extra.forbid

    message: str = Field(
        ...,
        description="Short promotional message (max 200 characters) containing exactly one HTTP/HTTPS CTA URL.",
    )

    if PYDANTIC_V2:
        @field_validator("message")
        @classmethod
        def validate_message_constraints(cls, value: str) -> str:
            extract_and_validate_single_cta_url(value)
            return value
    else:
        @validator("message")
        def validate_message_constraints(cls, value: str) -> str:
            extract_and_validate_single_cta_url(value)
            return value

    @property
    def cta_url(self) -> str:
        return extract_and_validate_single_cta_url(self.message)


class PlatformResult(BaseModel):
    """Individual platform publishing outcome."""

    platform: str = Field(..., description="Platform name")
    status: Literal["success", "failed"] = Field(
        ..., description="Publishing status (success or failed)"
    )
    posted_url: Optional[str] = Field(
        default=None, description="Published content URL if successful"
    )
    public_access: bool = Field(
        default=False, description="Whether the published content is publicly accessible"
    )
    date: Optional[str] = Field(
        default=None, description="Posting date (YYYY-MM-DD)"
    )
    time: Optional[str] = Field(
        default=None, description="Posting time (HH:MM:SS)"
    )
    error: Optional[str] = Field(
        default=None, description="Error details if posting failed"
    )


class PostingResponse(BaseModel):
    """Aggregated response returned by POST /posting."""

    success: bool = Field(
        ..., description="True if at least one platform succeeded, False if all failed"
    )
    results: List[PlatformResult] = Field(
        ..., description="Per-platform publishing outcomes"
    )
