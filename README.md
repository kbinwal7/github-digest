# GitHub Digest: AI Open Source Contribution Scout

An AI-powered dashboard and RAG pipeline that surface actionable open-source contribution opportunities using Qdrant Cloud and Google Gemini.

---

## Architecture & RAG Pipeline

* **Data Ingestion:** Fetches open issues from the GitHub REST API and filters out pull requests, closed tasks, and stale data.
* **Vector Embeddings:** Generates 768-dimensional dense vectors using Google Gemini's `text-embedding-004`.
* **Vector Storage:** Stores vectors and associated metadata in Qdrant Cloud for cosine-similarity semantic search.
* **LLM Matchmaking:** Uses Gemini 2.5 Flash to synthesize retrieved issues into structured maintainer guidance.

---

## Key Features

* **Semantic Search:** Allows developers to query contribution opportunities using natural language queries instead of rigid tag filters.
* **On-Demand Indexing:** Vectorizes open issues for newly queried public repositories in real time.
* **Maintainer Recommendations:** Produces concise summaries and initial repository entry points for retrieved tasks.
* **Activity Analytics:** Displays high-level repository statistics including commit, pull request, and issue velocity.

---

## Performance Optimizations

* **Stale Data Cleanup:** Excludes closed issues, pull requests, and items older than 30 days to maximize signal-to-noise ratio.
* **Payload Truncation:** Truncates issue descriptions to 1,000 characters to reduce embedding token costs and storage footprints.
* **Batch Embedding:** Embeds issue batches in a single concurrent network request to minimize API latency.
* **Deduplication Check:** Queries Qdrant prior to fetching data to eliminate re-indexing of previously cached repositories.

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

* **Environment Setup:** Clone the repository and install dependencies listed in `requirements.txt`.
* **Secrets Configuration:** Add `GITHUB_TOKEN`, `GEMINI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY` to a `.env` file.
* **Application Execution:** Run `streamlit run app.py` to start the local dashboard server.