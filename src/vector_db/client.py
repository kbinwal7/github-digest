import os
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from src.models.issue_schema import VectorIssuePayload

COLLECTION_NAME = "github-issue-digest"
VECTOR_DIMENSION = 768  # text-embedding-004 default size


class IssueVectorStore:
    def __init__(self):
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Creates the collection in Qdrant Cloud if it doesn't exist yet,
        and makes sure it has a payload index on 'repo'.

        Qdrant requires an explicit index on any field you filter by - it's
        not created automatically just because the field shows up in a
        payload. Without it, both is_repo_indexed() and the repo_filter in
        search_similar_issues() 400.
        """
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_DIMENSION, distance=Distance.COSINE
                ),
            )

        collection_info = self.qdrant.get_collection(COLLECTION_NAME)
        existing_indexes = collection_info.payload_schema or {}
        if "repo" not in existing_indexes:
            self.qdrant.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="repo",
                field_schema=PayloadSchemaType.KEYWORD,
            )

    # REQUIREMENT 4: Deduplication check
    def is_repo_indexed(self, repo_name: str) -> bool:
        """Check whether Qdrant already holds vectors for this repository."""
        records, _ = self.qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="repo", match=MatchValue(value=repo_name))]
            ),
            limit=1,
        )
        return len(records) > 0

    # REQUIREMENT 3: Batch embedder
    def batch_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds multiple texts via Gemini, chunked and paced to stay under
        rate limits, with backoff-and-retry on transient 429s.

        A smaller chunk size (vs. the API's 100-item hard cap) keeps each
        request's token count well under typical tokens-per-minute quotas,
        and the short pause between chunks keeps requests-per-minute in
        check too. If you're still hitting 429s after this, it's likely a
        daily quota (RPD) issue rather than a burst - that needs a billing
        upgrade on the Google Cloud project, not more retries.
        """
        if not texts:
            return []

        chunk_size = 20
        vectors: List[List[float]] = []
        for start in range(0, len(texts), chunk_size):
            chunk = texts[start : start + chunk_size]
            vectors.extend(self._embed_chunk_with_retry(chunk))
            if start + chunk_size < len(texts):
                time.sleep(1)  # brief pause to avoid bursting the RPM limit
        return vectors

    def _embed_chunk_with_retry(
        self, chunk: List[str], max_retries: int = 5
    ) -> List[List[float]]:
        delay_seconds = 2
        for attempt in range(max_retries):
            try:
                response = self.gemini.models.embed_content(
                    model="gemini-embedding-001",
                    contents=chunk,
                    config=types.EmbedContentConfig(output_dimensionality=VECTOR_DIMENSION),
                )
                return [item.values for item in response.embeddings]
            except Exception as exc:
                is_transient = any(
                    marker in str(exc)
                    for marker in ("RESOURCE_EXHAUSTED", "429", "UNAVAILABLE", "503")
                )
                if not is_transient or attempt == max_retries - 1:
                    raise
                time.sleep(delay_seconds)
                delay_seconds *= 2
        return []  # unreachable, keeps type checkers happy

    def upsert_issues(self, formatted_payloads: List[Dict[str, Any]]):
        """Batch-embeds and upserts issue payloads into Qdrant Cloud."""
        if not formatted_payloads:
            return

        texts = [item["text"] for item in formatted_payloads]
        vectors = self.batch_embed_texts(texts)

        points = []
        for item, vector in zip(formatted_payloads, vectors):
            points.append(
                PointStruct(
                    # NOTE: use a deterministic hash, not builtin hash().
                    # hash() is randomized per process (PYTHONHASHSEED), so
                    # the same issue would get a different point id on every
                    # run, silently defeating de-duplication/updates.
                    id=VectorIssuePayload.stable_point_id(item["id"]),
                    vector=vector,
                    payload={
                        "issue_id_str": item["id"],
                        "text": item["text"],
                        **item["metadata"],
                    },
                )
            )

        self.qdrant.upsert(collection_name=COLLECTION_NAME, points=points)

    def search_similar_issues(
        self, query: str, repo_filter: Optional[str] = None, limit: int = 5
    ):
        """Semantic search using a Gemini query embedding.

        Newer qdrant-client releases dropped the old .search() method in
        favor of .query_points(), which wraps its hits in a QueryResponse
        (access them via .points) rather than returning a bare list.
        """
        query_vector = self.batch_embed_texts([query])[0]

        qdrant_filter = None
        if repo_filter:
            qdrant_filter = Filter(
                must=[FieldCondition(key="repo", match=MatchValue(value=repo_filter))]
            )

        response = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
        )
        return response.points