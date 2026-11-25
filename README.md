# GitHub Digest --- AI Open-Source Contribution Scout

GitHub Digest helps developers find meaningful open-source work without
manually browsing hundreds of issues. Describe the kind of work you want
to do, explore repository activity, and discover open issues that match
your interests through semantic search and AI-generated contribution
guidance.

The project combines the GitHub REST API, Google Gemini embeddings and
generation, and Qdrant vector search in a FastAPI application with a
custom HTML/CSS/JavaScript frontend.

> **Project idea:** Reduce the friction between wanting to contribute to
> open source and finding a task that matches your interests and skills.

------------------------------------------------------------------------

## Features

-   **Repository activity digest:** Explore commits, pull requests, and
    issues within a selected date range.
-   **Concurrent GitHub collection:** Fetch activity categories
    concurrently, with bounded pagination.
-   **Semantic issue search:** Describe a contribution in natural
    language instead of relying only on labels or keywords.
-   **AI contribution guidance:** Generate practical guidance from
    retrieved issues to help contributors understand potential next
    steps.
-   **Gemini embeddings:** Use `RETRIEVAL_DOCUMENT` for indexed issue
    content and `RETRIEVAL_QUERY` for search queries.
-   **Qdrant vector search:** Store issue vectors and metadata for
    similarity-based retrieval.
-   **Safe advice rendering:** Escape model-generated HTML and render a
    deliberately limited Markdown subset on the frontend.
-   **Docker-ready deployment:** Run locally or deploy the container to
    a compatible hosting platform.
-   **Evaluation foundation:** Measure retrieval quality and latency
    using saved evaluation runs.

## How it works

``` text
                   Browser
          HTML / CSS / JavaScript
                     |
                     v
                  FastAPI
          /api/digest | /api/search
                     |
          +----------+-----------+
          |                      |
          v                      v
   GitHub REST API          RAG pipeline
   via async httpx                |
          |                Gemini embeddings
          v                      |
   Commits / PRs / Issues         v
          |                    Qdrant
          v                      |
   Normalized digest              v
                          Relevant open issues
                                   |
                                   v
                           Gemini generation
                                   |
                                   v
                       Contribution guidance
```

### RAG pipeline

1.  Collect open issues from a GitHub repository.
2.  Filter out pull requests, closed issues, and issues outside the
    configured staleness window.
3.  Prepare issue text and metadata for embedding.
4.  Embed issue documents with Gemini using the `RETRIEVAL_DOCUMENT`
    task type.
5.  Store vectors and payloads in Qdrant.
6.  Embed the user's natural-language query using `RETRIEVAL_QUERY`.
7.  Retrieve the most relevant issues from Qdrant.
8.  Use Gemini to produce contribution guidance grounded in the
    retrieved issue context.

The index is refreshed when a digest is requested. Deterministic point
IDs allow existing issue vectors to be updated rather than duplicated.

## Architecture

``` text
app/
├── api/          # FastAPI routes and request/response contracts
├── core/         # Settings and application configuration
├── services/     # GitHub collection, digest, indexing, Qdrant and RAG logic
├── static/       # HTML, CSS and JavaScript frontend
└── main.py       # Application setup and lifespan-managed resources

evals/            # Retrieval evaluation runner and dataset guidance
tests/            # Automated tests
Dockerfile
render.yaml
requirements.txt
pyproject.toml
.env.example
```

`app/main.py` manages application startup and shared resources. API
routes live in `app/api/`, while GitHub collection, indexing, retrieval,
and generation are separated into services.

## Tech stack

  Layer             Technology
  ----------------- -----------------------
  Frontend          HTML, CSS, JavaScript
  API               FastAPI
  HTTP client       HTTPX (async)
  Repository data   GitHub REST API
  Embeddings        Google Gemini
  Generation        Google Gemini
  Vector database   Qdrant Cloud
  Configuration     Pydantic Settings
  Tests             pytest
  Deployment        Docker / Render

------------------------------------------------------------------------

## Run locally

### Requirements

-   Python 3.11 or newer
-   A GitHub token is recommended for higher GitHub API rate limits.
-   Gemini and Qdrant credentials are required for semantic indexing and
    AI recommendations.

### 1. Clone the repository

``` bash
git clone https://github.com/kbinwal7/github-digest.git
cd github-digest
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

``` powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and add your credentials.

**Windows PowerShell**

``` powershell
Copy-Item .env.example .env
```

**macOS / Linux**

``` bash
cp .env.example .env
```

Example configuration:

``` env
GITHUB_TOKEN=your_github_token

GEMINI_API_KEY=your_gemini_api_key
GEMINI_GENERATION_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768

QDRANT_URL=https://your-cluster-url
QDRANT_API_KEY=your_qdrant_api_key

GITHUB_MAX_PAGES=10
STALE_AFTER_DAYS=730
ISSUE_TEXT_MAX_CHARS=8000
```

Use the exact variable names and defaults supported by the current
application configuration. Model availability can vary by Google AI
account, region, and API access; choose a currently supported generation
model in your environment if the configured model is unavailable.

**Important:** Never commit `.env`, API keys, or other credentials to
Git. The embedding dimension configured for Qdrant must match the output
dimension of the selected embedding model. Changing the embedding model
or dimension for an existing collection may require a collection
migration or recreation and re-indexing.

### 5. Start the application

``` bash
uvicorn app.main:app --reload
```

Open:

-   Application: http://localhost:8000
-   API documentation: http://localhost:8000/docs
-   Health check: http://localhost:8000/health

Public repository digests can work without Gemini or Qdrant credentials.
Semantic indexing and AI advice require the corresponding services to be
configured; RAG endpoints provide setup guidance when they are
unavailable.

------------------------------------------------------------------------

## API

### `POST /api/digest`

Collect repository activity for a date range.

Example request:

``` json
{
  "repository": "owner/repo",
  "start_date": "2026-11-01",
  "end_date": "2026-11-25"
}
```

The response includes normalized commits, pull requests, issues,
collection timestamps, pagination truncation status, and issue-indexing
status. The activity categories are fetched concurrently.

### `POST /api/search`

Search for contribution opportunities using natural language.

Example request:

``` json
{
  "query": "beginner friendly Python documentation tasks",
  "repository": "owner/repo",
  "limit": 5
}
```

The repository filter is optional. The response contains matching issue
metadata and generated contribution guidance.

### `GET /api/repos/{owner}/{repo}/status`

Returns public repository metadata from GitHub.

### `GET /health`

Returns the application health status.

------------------------------------------------------------------------

## Docker

Build the image:

``` bash
docker build -t github-digest .
```

Run it:

``` bash
docker run --env-file .env -p 8000:8000 github-digest
```

Then open http://localhost:8000.

## Deploy to Render

The repository includes a `render.yaml` deployment configuration. You
can connect `kbinwal7/github-digest` to Render and deploy the `main`
branch.

Add the required environment variables in the Render dashboard:

-   `GITHUB_TOKEN`
-   `GEMINI_API_KEY`
-   `QDRANT_URL`
-   `QDRANT_API_KEY`

Also configure the Gemini model and embedding settings if they differ
from the application defaults. Do not put secrets in `render.yaml` or
commit them to the repository.

Hosting-provider free plans, sleeping behavior, and usage limits can
change. Check the provider's current plan details before deployment.

------------------------------------------------------------------------

## Tests

Run the test suite:

``` bash
pytest -q
```

The tests cover core application behavior such as repository parsing,
normalization, issue filtering, and HTTP routes. Unit tests should mock
external GitHub, Gemini, and Qdrant calls rather than making live
requests.

## RAG evaluation

The project includes retrieval metric implementations and a runner for
saved evaluation results.

``` bash
python -m evals.run_eval path/to/retrieval-run.json --out evals/results
```

See `evals/datasets/README.md` for the input format and dataset
guidance.

The evaluation metrics include:

-   Recall@1, Recall@3, Recall@5, and Recall@10
-   Mean Reciprocal Rank (MRR)
-   nDCG@1, nDCG@3, nDCG@5, and nDCG@10
-   p50 and p95 latency when latency measurements are supplied

No retrieval-quality or latency benchmark numbers are claimed here.
Build frozen issue snapshots and a manually labelled relevance set
before reporting performance. Automated generation faithfulness checks
and LLM-judge scores are future evaluation work.

## Current limitations and next steps

-   Retrieval currently uses dense vectors. BM25, hybrid retrieval with
    reciprocal rank fusion, reranking, MMR, query expansion, and recency
    or label boosts are potential experiments.
-   Issue comments, repository README and CONTRIBUTING files, and
    file-tree context are not yet part of the indexed context. Generated
    first steps should therefore remain conservative.
-   The index refreshes on demand when a digest is requested; it is not
    a scheduled background sync.
-   The evaluation runner consumes saved retrieval outputs. Dataset
    capture, query generation, human annotation, and automated
    generation judging still need to be completed.
-   The FastAPI frontend recreates the former Streamlit experience using
    standard web technologies; it is not intended to be a
    pixel-identical copy.

## Security

-   Keep `.env` and all API credentials out of version control.
-   Use environment variables for deployment secrets.
-   Treat repository issue content and model output as untrusted input.
-   Keep frontend rendering escaped and sanitized; do not inject raw
    model-generated HTML.

## License

See [LICENSE](LICENSE).
