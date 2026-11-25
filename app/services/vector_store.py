import hashlib, time
from typing import Any
from app.core.config import Settings

class IssueVectorStore:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key: raise RuntimeError("GEMINI_API_KEY is not configured.")
        if not settings.qdrant_url: raise RuntimeError("QDRANT_URL is not configured.")
        try:
            from google import genai
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError("Install google-genai and qdrant-client to enable RAG.") from exc
        self._genai=genai
        self.settings=settings
        from google import genai
        from qdrant_client import QdrantClient
        self._genai=genai
        self.gemini=genai.Client(api_key=settings.gemini_api_key)
        self.qdrant=QdrantClient(url=settings.qdrant_url,api_key=settings.qdrant_api_key)
        self._ensure_collection()

    def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
        from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
        names=[x.name for x in self.qdrant.get_collections().collections]
        if self.settings.qdrant_collection not in names:
            self.qdrant.create_collection(collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=self.settings.embedding_dimension,distance=Distance.COSINE))
        schema=self.qdrant.get_collection(self.settings.qdrant_collection).payload_schema or {}
        if "repo" not in schema:
            self.qdrant.create_payload_index(collection_name=self.settings.qdrant_collection,
                field_name="repo",field_schema=PayloadSchemaType.KEYWORD)

    @staticmethod
    def point_id(issue_id: str) -> int:
        return int(hashlib.sha256(issue_id.encode()).hexdigest()[:16],16)

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types
        from google.genai import types
        vectors=[]
        for offset in range(0,len(texts),20):
            batch=texts[offset:offset+20]
            for attempt in range(5):
                try:
                    response=self.gemini.models.embed_content(model=self.settings.gemini_embedding_model,
                        contents=batch,config=types.EmbedContentConfig(
                            task_type=task_type,output_dimensionality=self.settings.embedding_dimension))
                    vectors.extend([item.values for item in response.embeddings]); break
                except Exception as exc:
                    transient=any(x in str(exc) for x in ("429","RESOURCE_EXHAUSTED","503","UNAVAILABLE"))
                    if not transient or attempt==4: raise
                    time.sleep(2**attempt)
        return vectors

    def is_repo_indexed(self, repo: str) -> bool:
        points,_=self.qdrant.scroll(collection_name=self.settings.qdrant_collection,
            scroll_filter=Filter(must=[FieldCondition(key="repo",match=MatchValue(value=repo))]),limit=1)
        return bool(points)

    def upsert_issues(self, items: list[dict]) -> int:
        from qdrant_client.models import PointStruct
        from qdrant_client.models import PointStruct
        if not items:return 0
        vectors=self._embed([x["text"] for x in items],"RETRIEVAL_DOCUMENT")
        points=[PointStruct(id=self.point_id(x["id"]),vector=v,
            payload={"issue_id_str":x["id"],"text":x["text"],**x["metadata"]}) for x,v in zip(items,vectors)]
        self.qdrant.upsert(collection_name=self.settings.qdrant_collection,points=points)
        return len(points)


    def delete_repo_issues(self, repo: str) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        self.qdrant.delete(collection_name=self.settings.qdrant_collection,
            points_selector=Filter(must=[FieldCondition(key="repo",match=MatchValue(value=repo))]),
            wait=True)

    def search(self, query: str, repo: str | None=None, limit: int=5):
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        vector=self._embed([query],"RETRIEVAL_QUERY")[0]
        query_filter=Filter(must=[FieldCondition(key="repo",match=MatchValue(value=repo))]) if repo else None
        return self.qdrant.query_points(collection_name=self.settings.qdrant_collection,
            query=vector,query_filter=query_filter,limit=limit).points
