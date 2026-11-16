"""FastAPI entrypoint for the Automated Multi-Platform Posting System."""

from fastapi import Depends, FastAPI
from app.config import Settings, get_settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "FastAPI application that validates a short promotional message (max 200 characters, "
        "1 valid CTA link) and concurrently publishes it across 6 third-party websites, "
        "developer portals, social platforms, and LLM platforms."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def get_posting_service(settings: Settings = Depends(get_settings)) -> PostingService:
    """Dependency provider for PostingService."""
    return PostingService(settings=settings)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "automated-multi-platform-posting"}


@app.post(
    "/posting",
    response_model=PostingResponse,
    summary="Publish a short message across multiple third-party platforms",
    tags=["Posting"],
)
async def create_posting(
    payload: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    """Validate the incoming message and publish concurrently across all integrated platforms."""
    return await service.publish_all(payload)
