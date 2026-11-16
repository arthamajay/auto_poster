# Automated Multi-Platform Posting System

A production-ready **FastAPI** service that validates a short promotional message (≤ 200 characters, exactly one CTA link) and **concurrently publishes it across 6 third-party platforms** — developer portals, decentralised social networks, and an LLM showcase — returning a structured per-platform result for each attempt.

---

## Integrated Platforms

| # | Platform | Category | API Endpoint Used | Official Docs |
|---|---|---|---|---|
| 1 | **Telegraph (Telegra.ph)** | Publishing Portal | `POST /createPage` | [telegra.ph/api](https://telegra.ph/api) |
| 2 | **GitHub Gist** | Developer Portal | `POST /gists` | [docs.github.com/en/rest/gists](https://docs.github.com/en/rest/gists/gists) |
| 3 | **Dev.to (Forem)** | Tech Community | `POST /api/articles` | [developers.forem.com/api/v1](https://developers.forem.com/api/v1) |
| 4 | **Bluesky (AT Protocol)** | Social Microblogging | `POST /xrpc/com.atproto.repo.createRecord` | [bsky.network/docs](https://bsky.network/docs/bluesky-api/creating-a-post/) |
| 5 | **Mastodon** | Federated Social Network | `POST /api/v1/statuses` | [docs.joinmastodon.org](https://docs.joinmastodon.org/methods/statuses/) |
| 6 | **Groq LLM Portal** | LLM Platform | `POST /openai/v1/chat/completions` | [console.groq.com/docs](https://console.groq.com/docs/api-reference) |

> **Telegraph works with zero manual setup.** If `TELEGRAPH_ACCESS_TOKEN` is left blank, the app auto-provisions an anonymous account token via `createAccount` on first use.

---

## Project Structure

```text
automated-posting/
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + POST /posting route
│   ├── schemas.py                # Pydantic models & strict CTA URL/length validators
│   ├── config.py                 # pydantic-settings environment configuration
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract BasePlatformClient with fault isolation
│   │   ├── telegraph_platform.py
│   │   ├── github_gist.py
│   │   ├── devto.py
│   │   ├── bluesky.py
│   │   ├── mastodon.py
│   │   └── groq_llm_portal.py
│   └── services/
│       ├── __init__.py
│       └── posting_service.py    # asyncio.gather concurrent dispatcher
│
├── tests/
│   ├── __init__.py
│   └── test_posting.py           # Pytest validation & fault-tolerance suite (8 tests)
│
├── pytest.ini
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup & Execution

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/<your-username>/automated-posting.git
cd automated-posting
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials. Only the platforms you configure will succeed; unconfigured platforms fail gracefully with a clear error message.

| Variable | Required For |
|---|---|
| `GITHUB_TOKEN` | GitHub Gist (PAT with `gist` scope) |
| `DEVTO_API_KEY` | Dev.to (from Settings → Extensions) |
| `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` | Bluesky |
| `MASTODON_ACCESS_TOKEN` | Mastodon (OAuth, `write:statuses` scope) |
| `GROQ_API_KEY` | Groq LLM Portal |
| `TELEGRAPH_ACCESS_TOKEN` | Telegraph — optional, auto-provisioned if blank |

### 4. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Interactive Swagger UI: **http://localhost:4000/docs**

### 5. Run the test suite

```bash
pytest -v
```

Expected output: **8 passed** in under 2 seconds.

---

## API Reference

### `POST /posting`

Publishes a message across all configured platforms concurrently.

**Request**

```http
POST http://localhost:4000/posting
Content-Type: application/json
```

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

**Input validation rules**
- Message must not exceed 200 characters.
- Message must contain exactly one valid `http://` or `https://` CTA link.
- Message must include descriptive text in addition to the link.
- Platform selection is handled internally — passing a `platforms` field returns a 422 error.

**Success Response — `200 OK`**

```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegraph",
      "status": "success",
      "posted_url": "https://telegra.ph/Featured-Update-11-16",
      "public_access": true,
      "date": "2026-11-16",
      "time": "15:25:10",
      "error": null
    },
    {
      "platform": "GitHub Gist",
      "status": "success",
      "posted_url": "https://gist.github.com/<user>/8f9d2a1b3c4e5f6a7b8c",
      "public_access": true,
      "date": "2026-11-16",
      "time": "15:25:11",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/<user>/check-out-our-latest-business-platform-3k9a",
      "public_access": true,
      "date": "2026-11-16",
      "time": "15:25:11",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/<handle>/post/3lb2x9k7m2p",
      "public_access": true,
      "date": "2026-11-16",
      "time": "15:25:12",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed: MASTODON_ACCESS_TOKEN is not configured in environment"
    },
    {
      "platform": "Groq LLM Portal",
      "status": "success",
      "posted_url": "https://telegra.ph/Groq-LLM-Syndicated-Post-11-16",
      "public_access": true,
      "date": "2026-11-16",
      "time": "15:25:12",
      "error": null
    }
  ]
}
```

**Validation Error Response — `422 Unprocessable Entity`**

Request missing a CTA link:
```json
{ "message": "Check out our latest business platform without any link" }
```

Response:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message must include exactly one valid CTA link (starting with http:// or https://).",
      "input": "Check out our latest business platform without any link"
    }
  ]
}
```

### `GET /health`

```json
{ "status": "healthy", "service": "automated-multi-platform-posting" }
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| `asyncio.gather` for all platforms | All 6 HTTP calls run concurrently; total latency ≈ slowest single platform |
| `BasePlatformClient.publish_safe` | Wraps every `_publish` in try/except; one platform's failure cannot affect others |
| `pydantic-settings` for config | Type-safe, validated environment loading with `.env` file support |
| Telegraph auto-provision | Zero-friction setup — works without any credentials for the demo |
| Rich-text facets on Bluesky | CTA link is clickable in the Bluesky app, not just plain text |
| Groq + Telegraph combo | Groq has no public post storage; Telegraph provides the persistent public URL |

---

## Tech Stack

- **Python 3.x**
- **FastAPI** — REST API framework
- **Uvicorn** — ASGI server
- **Pydantic v2** — request/response validation
- **pydantic-settings** — environment configuration
- **HTTPX** — async HTTP client
- **python-dotenv** — `.env` loading
- **pytest + pytest-asyncio** — test suite
