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
