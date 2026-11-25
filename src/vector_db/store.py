import os
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma  # Or Pinecone / Qdrant
from src.models.issue_schema import VectorIssuePayload

# Initialize local or cloud Vector DB
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = Chroma(
    collection_name="github_issues",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

def store_issues_in_vector_db(raw_issues: List[dict], repo_name: str):
    """Filter, transform, and store raw GitHub issues into the vector DB."""
    
    documents = []
    metadatas = []
    ids = []

    for issue in raw_issues:
        # Skip Pull Requests (GitHub API treats PRs as issues, but PRs contain 'pull_request' key)
        if "pull_request" in issue:
            continue
            
        # Optional: Only ingest open issues
        if issue.get("state") != "open":
            continue

        payload = VectorIssuePayload.from_github_issue(issue, repo_name)
        
        documents.append(payload.text)
        metadatas.append(payload.metadata)
        ids.append(payload.id)

    if documents:
        vector_store.add_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully vectorized and stored {len(documents)} issues for {repo_name}.")