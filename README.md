# GitHub Digest

GitHub Digest helps contributors explore repository activity and find open issues aligned with their interests. Version 2 serves a custom HTML/CSS/JavaScript interface from FastAPI and exposes JSON endpoints for digesting, indexing, searching and repository status.

## Features

- Activity digest for commits, pull requests and issues within a date window.
- Concurrent GitHub REST API collection with bounded pagination.
- Optional Gemini + Qdrant semantic issue indexing and recommendation generation.
- Gemini embedding task types: `RETRIEVAL_DOCUMENT` for indexed issues and `RETRIEVAL_QUERY` for searches.
- Safe client-side advice rendering: model output is HTML-escaped before a deliberately small Markdown subset is rendered.
- Docker deployment and pytest coverage.
- Retrieval evaluation metrics and a JSON-based experiment format.

## Architecture

```text
Browser (static HTML/CSS/JS)
        |
        v
FastAPI: /api/digest, /api/search, /api/repos/{owner}/{repo}/status
        |                         |
        v                         v
Async httpx -> GitHub REST     Gemini -> Qdrant
        |
        v
Normalized digest JSON
```

`app/main.py` owns application lifespan and shared clients. `app/api/` defines HTTP contracts. `app/services/` contains GitHub collection, digest construction, issue preparation, vector storage and RAG generation. `app/core/config.py` centralizes environment settings. `app/static/` contains the frontend.

## Requirements and local run

Python 3.11+ (Docker image uses Python 3.12).

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000. API docs: http://localhost:8000/docs. Health: http://localhost:8000/health.

Public repository digests work without credentials, though a `GITHUB_TOKEN` is recommended to raise GitHub's rate limit. Semantic indexing and AI advice require `GEMINI_API_KEY`, `QDRANT_URL`, and (for authenticated Qdrant Cloud) `QDRANT_API_KEY`. If these are absent, the digest UI and API remain available; RAG endpoints return HTTP 503 with setup guidance.

## API

### `POST /api/digest`

```json
{
  "repository": "owner/repo",
  "start_date": "2026-11-01",
  "end_date": "2026-11-25"
}
```

Returns normalized commits, pull requests, issues, collection timestamps, pagination truncation status and issue-indexing status. The three activity categories are fetched concurrently. The open-issue index refreshes on each digest call using deterministic point IDs, so existing issue vectors are updated rather than duplicated.

### `POST /api/search`

```json
{"query":"beginner friendly Python documentation tasks","repository":"owner/repo","limit":5}
```

Returns matched issue metadata and generated contribution advice. The repository filter is optional.

### `GET /api/repos/{owner}/{repo}/status`

Returns public repository metadata from GitHub.

### `GET /health`

Returns `{"status":"ok"}`.

## Configuration

Copy `.env.example` to `.env`. Important settings:

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | empty | Optional GitHub API token |
| `GEMINI_API_KEY` | empty | Gemini API key |
| `GEMINI_GENERATION_MODEL` | `gemini-3.8-flash` | Text generation model |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `EMBEDDING_DIMENSION` | `768` | Qdrant vector dimension |
| `QDRANT_URL` | empty | Qdrant endpoint |
| `QDRANT_API_KEY` | empty | Qdrant credential |
| `GITHUB_MAX_PAGES` | `10` | Max pages per GitHub category |
| `STALE_AFTER_DAYS` | `730` | Exclude older open issues from indexing |
| `ISSUE_TEXT_MAX_CHARS` | `8000` | Maximum embedded issue text length |

**Important:** changing the embedding model or vector dimension for an existing Qdrant collection requires a compatible collection migration/recreation. The configured dimension must match the model output.

## Docker

```bash
docker build -t github-digest .
docker run --env-file .env -p 8000:8000 github-digest
```

Render deployment is scaffolded in `render.yaml`. Add the environment variables in the Render dashboard. Free-tier sleep/cold-start and current plan limits are controlled by the host and may change; verify current provider pricing before choosing a deployment target.

## Tests

```bash
pytest -q
```

The tests cover repository parsing, normalization, issue filtering and HTTP health/home routes. External GitHub, Gemini and Qdrant calls are not made by the unit tests.

## RAG evaluation

The project includes metric implementations and a runner:

```bash
python -m evals.run_eval path/to/retrieval-run.json --out evals/results
```

Input schema and dataset guidance are in `evals/datasets/README.md`. Metrics include Recall@1/3/5/10, MRR, nDCG@1/3/5/10 and p50/p95 latency when latency values are supplied.

No benchmark numbers are claimed in this repository. The previous README's ingestion/cache latency and storage/capacity figures were not backed by a reproducible benchmark. Establish frozen issue snapshots and a manually labelled relevance set before reporting retrieval quality. Generation faithfulness and LLM-judge scores are not yet automated in this starter harness.

## Current limitations / next experiments

- Retrieval is dense-only. BM25, hybrid RRF, reranking, MMR, query expansion and recency/label boosts remain experiment candidates.
- Issue comments, repository README/CONTRIBUTING and file-tree context are not indexed yet; generated first steps must therefore stay conservative.
- The frontend is a custom implementation of the former Streamlit experience, not a pixel-identical port. Tabs, date controls, metrics and alerts are native HTML/CSS/JS.
- The evaluation runner consumes saved retrieval outputs; dataset capture, query generation, human annotation and automated generation judging are separate follow-up work.
- The current index refresh is on-demand when a digest runs, not a scheduled background sync.

## License

See [LICENSE](LICENSE).
