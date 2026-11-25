from datetime import date
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.services.digest import build_digest
from app.services.github import parse_repository, GitHubAPIError
from app.services.indexing import prepare_issues

router=APIRouter(prefix="/api")

class DigestRequest(BaseModel):
    repository: str
    start_date: date
    end_date: date

class SearchRequest(BaseModel):
    query: str = Field(min_length=3,max_length=1000)
    repository: str | None = None
    limit: int = Field(default=5,ge=1,le=10)

def translate_github_error(exc: GitHubAPIError):
    if exc.status_code==404: raise HTTPException(404,"Repository not found, or it is private.")
    if exc.status_code==401: raise HTTPException(401,"GitHub rejected the token.")
    if exc.status_code==403 and exc.headers.get("x-ratelimit-remaining")=="0":
        raise HTTPException(429,"GitHub API rate limit reached. Configure GITHUB_TOKEN.")
    raise HTTPException(exc.status_code,exc.message[:300])

@router.post("/digest")
async def digest(body: DigestRequest, request: Request):
    if body.start_date>body.end_date: raise HTTPException(422,"Start date must be on or before end date.")
    try:
        result=await build_digest(body.repository,body.start_date,body.end_date,
            request.app.state.github,request.app.state.settings.github_max_pages)
        owner,repo=parse_repository(body.repository)
        repo_slug=f"{owner}/{repo}"
        # Index a complete open-issue snapshot, not just the date-window subset.
        raw, truncated=await request.app.state.github.fetch_pages(owner,repo,"issues",state="open",
            max_pages=request.app.state.settings.github_max_pages)
        result["indexing"]={"repository":repo_slug,"indexed":0,"status":"not_configured"}
        if request.app.state.vector_store:
            payloads=prepare_issues(raw,repo_slug,request.app.state.settings)
            # Replace the repo snapshot only when pagination completed; never
            # erase a larger existing index after a capped/partial GitHub fetch.
            if not truncated:
                request.app.state.vector_store.delete_repo_issues(repo_slug)
            count=request.app.state.vector_store.upsert_issues(payloads)
            result["indexing"]={"repository":repo_slug,"indexed":count,"truncated":truncated,
                                "status":"indexed" if not truncated else "partial_refresh"}
        return result
    except ValueError as exc: raise HTTPException(422,str(exc))
    except GitHubAPIError as exc: translate_github_error(exc)

@router.post("/search")
def search(body: SearchRequest, request: Request):
    store=request.app.state.vector_store
    rag=request.app.state.rag
    if not store or not rag: raise HTTPException(503,"RAG is not configured. Set Gemini and Qdrant environment variables.")
    try:
        repo=None
        if body.repository:
            owner,name=parse_repository(body.repository); repo=f"{owner}/{name}"
        points=store.search(body.query,repo,body.limit)
        matches=[]
        for p in points:
            payload=p.payload or {}
            matches.append({"score":p.score,"issue_id":payload.get("issue_id_str"),
                "repo":payload.get("repo"),"title":payload.get("title"),"url":payload.get("url"),
                "labels":payload.get("labels",[]),"text":payload.get("text","")})
        advice=rag.generate_recommendation(body.query,points)
        return {"matches":matches,"advice":advice}
    except ValueError as exc: raise HTTPException(422,str(exc))

@router.get("/repos/{owner}/{repo}/status")
async def repo_status(owner: str, repo: str, request: Request):
    try: return await request.app.state.github.repository_status(owner,repo)
    except GitHubAPIError as exc: translate_github_error(exc)
