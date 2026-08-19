from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Commit(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    url: str

class PullRequest(BaseModel):
    number: int
    title: str
    state: str
    author: str
    created_at: str
    merged_at: Optional[str] = None
    url: str
    body: Optional[str] = None

class Issue(BaseModel):
    number: int
    title: str
    state: str
    author: str
    created_at: str
    closed_at: Optional[str] = None
    url: str
    body: Optional[str] = None
    labels: list[str] = []
    
    
    
    
def normalize_commit(raw: dict) -> Commit:
    return Commit(
        sha=raw["sha"][:7],
        message=raw["commit"]["message"].split("\n")[0],
        author=raw["commit"]["author"]["name"],
        date=raw["commit"]["author"]["date"],
        url=raw["html_url"]
    )

def normalize_pull_request(raw: dict) -> PullRequest:
    return PullRequest(
        number=raw["number"],
        title=raw["title"],
        state=raw["state"],
        author=raw["user"]["login"],
        created_at=raw["created_at"],
        merged_at=raw.get("merged_at"),
        url=raw["html_url"],
        body=raw.get("body")
    )

def normalize_issue(raw: dict) -> Issue | None:
    # Skip pull requests (GitHub includes them in the issues endpoint)
    if "pull_request" in raw:
        return None

    labels = [label["name"] for label in raw.get("labels", [])]

    return Issue(
        number=raw["number"],
        title=raw["title"],
        state=raw["state"],
        author=raw["user"]["login"],
        created_at=raw["created_at"],
        closed_at=raw.get("closed_at"),
        url=raw["html_url"],
        body=raw.get("body"),
        labels=labels
    )