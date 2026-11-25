<<<<<<< HEAD
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
=======
# GitHub Digest: AI Open Source Contribution Scout

An AI-powered dashboard and RAG pipeline that surfaces actionable open-source contribution opportunities using Qdrant Cloud and Google Gemini.



https://github.com/user-attachments/assets/9c8dad27-aac0-48dd-89ba-6587e63d059b




**Live Demo:** [GitHub Digest](https://app-digest-caage9up7yluka9xnblxuc.streamlit.app/)


---

## Architecture & RAG Pipeline

* **Data Ingestion:** Fetches open issues from the GitHub REST API and filters out pull requests, closed tasks, and stale data.
* **Vector Embeddings:** Generates 768-dimensional dense vectors using Google Gemini's `text-embedding-004`.
* **Vector Storage:** Stores vectors and associated metadata in Qdrant Cloud for cosine-similarity semantic search.
* **LLM Matchmaking:** Uses Gemini 2.5 Flash to synthesize retrieved issues into structured maintainer guidance.

### Request Flow

```text
GitHub Repository
       |
       v
GitHub REST API
       |
       v
Issue Filtering
       |
       +----> Remove closed / stale / PR records
       |
       v
Payload Truncation
       |
       v
Batch Embedding
       |
       v
Google Gemini Embeddings
       |
       v
Qdrant Cloud
       |
       v
Semantic Search
       |
       v
Top Matching Issues
       |
       v
Gemini 2.5 Flash
       |
       v
Contribution Guidance
```

---

## Key Features

* **Semantic Search:** Allows developers to query contribution opportunities using natural language queries instead of rigid tag filters.
* **On-Demand Indexing:** Vectorizes open issues for newly queried public repositories in real time.
* **Maintainer Recommendations:** Produces concise summaries and initial repository entry points for retrieved tasks.
* **Activity Analytics:** Displays high-level repository statistics including commit, pull request, and issue activity.

---

## Gemini Load Handling

The pipeline is designed to avoid unnecessary Gemini API calls and keep embedding workloads efficient when indexing repositories with many issues.

* **Batch Embedding:** Issues are collected into a payload batch before embedding rather than sending one Gemini request per issue. This reduces request overhead and improves ingestion throughput.
* **Payload Truncation:** Issue descriptions are limited to 1,000 characters before embedding. This keeps the embedding input focused while reducing token usage.
* **Repository-Level Deduplication:** Before indexing, the application checks Qdrant to determine whether the repository has already been indexed. Cached repositories are not embedded again.
* **Filtered Input:** Only relevant open issues are passed into the embedding pipeline. Pull requests, closed issues, stale records, and other filtered records are excluded before Gemini processing.
* **Two-Stage AI Usage:** Gemini embeddings are used during indexing, while Gemini 2.5 Flash is only invoked when generating contribution guidance from the retrieved matches. Semantic retrieval itself is handled by Qdrant.
* **On-Demand Processing:** Repositories are indexed only when requested instead of continuously processing GitHub repositories in the background.

This keeps Gemini usage focused on the parts of the pipeline where generative or semantic processing provides the most value.

---

## Performance Optimizations

* **Stale Data Cleanup:** Excludes closed issues, pull requests, and items older than 30 days to maximize signal-to-noise ratio.
* **Payload Truncation:** Truncates issue descriptions to 1,000 characters to reduce embedding token costs and storage footprints.
* **Batch Embedding:** Embeds issue batches in a single concurrent network request to minimize API latency and request overhead.
* **Deduplication Check:** Queries Qdrant prior to fetching data to eliminate re-indexing of previously cached repositories.
* **Vector Database Retrieval:** Uses Qdrant for similarity search rather than sending the full issue corpus to Gemini.

---

## Performance & Storage Metrics

* **Memory Footprint:** Uses approximately 6.5 KB to 7 KB of storage per indexed issue.
* **Cluster Capacity:** Supports over 100,000 active issue vectors on Qdrant Cloud's free tier.
* **Ingestion Latency:** Indexes 30 new issues in approximately 1.1 to 1.5 seconds.
* **Cache Latency:** Serves semantic search requests for cached repositories in under 100 milliseconds.

---

## Repository Structure

* `app.py`: Contains the Streamlit dashboard user interface and workflow orchestration.
* `src/models/issue_schema.py`: Implements Pydantic data schemas and issue filtering logic.
* `src/vector_db/client.py`: Manages Qdrant Cloud vector operations and Gemini batch embedding calls.
* `src/analysis/rag_engine.py`: Constructs retrieval prompts and handles LLM response synthesis.
* `src/github/`: Contains specialized API modules for fetching commits, issues, and pull requests.

---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-directory>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Secrets

Create a `.env` file with the required credentials:

```env
GITHUB_TOKEN=your_github_token
GEMINI_API_KEY=your_gemini_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
```

### 4. Run the Application

```bash
streamlit run app.py
```

The dashboard will be available at the local Streamlit address shown in your terminal.

---

## Tech Stack

| Component       | Technology       |
| --------------- | ---------------- |
| Frontend        | Streamlit        |
| Repository Data | GitHub REST API  |
| Embeddings      | Google Gemini    |
| LLM             | Gemini 2.5 Flash |
| Vector Database | Qdrant Cloud     |
| Data Validation | Pydantic         |
| Language        | Python           |

---

## Project Goal

GitHub Digest is designed to reduce the friction between wanting to contribute to open source and finding a task that matches a developer's interests and skill set.

Instead of manually browsing hundreds of GitHub issues, developers can describe the type of work they want to do and use semantic retrieval to surface relevant contribution opportunities.
>>>>>>> origin/main
