import asyncio
from datetime import date, datetime, time, timezone
from typing import Any
from .github import GitHubClient, parse_repository, in_window

def normalize_commit(raw: dict) -> dict:
    commit=raw.get("commit",{})
    author=commit.get("author") or {}
    return {"sha":raw.get("sha","")[:7],"message":(commit.get("message") or "").split("\n")[0],
            "author":author.get("name") or (raw.get("author") or {}).get("login","Unknown"),
            "date":author.get("date",""),"url":raw.get("html_url","")}

def normalize_pull_request(raw: dict) -> dict:
    return {"number":raw.get("number"),"title":raw.get("title",""),"state":raw.get("state",""),
            "author":(raw.get("user") or {}).get("login","Unknown"),"created_at":raw.get("created_at",""),
            "merged_at":raw.get("merged_at"),"url":raw.get("html_url",""),"body":raw.get("body")}

def normalize_issue(raw: dict) -> dict | None:
    if "pull_request" in raw: return None
    return {"number":raw.get("number"),"title":raw.get("title",""),"state":raw.get("state",""),
            "author":(raw.get("user") or {}).get("login","Unknown"),"created_at":raw.get("created_at",""),
            "closed_at":raw.get("closed_at"),"url":raw.get("html_url",""),"body":raw.get("body"),
            "labels":[x.get("name","") if isinstance(x,dict) else str(x) for x in raw.get("labels",[])]}

async def build_digest(repository: str, start: date, end: date, client: GitHubClient, max_pages: int=10) -> dict:
    owner, repo=parse_repository(repository)
    since=datetime.combine(start,time.min,timezone.utc).isoformat()
    until=datetime.combine(end,time.max,timezone.utc).isoformat()
    commits_task=client.fetch_pages(owner,repo,"commits",since=since,until=until,max_pages=max_pages)
    prs_task=client.fetch_pages(owner,repo,"pulls",max_pages=max_pages)
    issues_task=client.fetch_pages(owner,repo,"issues",max_pages=max_pages)
    (commits,trunc_c),(prs,trunc_p),(issues,trunc_i)=await asyncio.gather(commits_task,prs_task,issues_task)
    norm_commits=[normalize_commit(x) for x in commits]
    norm_prs=[normalize_pull_request(x) for x in prs]
    norm_issues=[x for raw in issues if (x:=normalize_issue(raw)) is not None]
    return {"repository":f"{owner}/{repo}","start_date":start.isoformat(),"end_date":end.isoformat(),
            "collected_at":datetime.now(timezone.utc).isoformat(),
            "commits":[x for x in norm_commits if in_window(x["date"],start,end)],
            "pull_requests":[x for x in norm_prs if in_window(x["created_at"],start,end)],
            "issues":[x for x in norm_issues if in_window(x["created_at"],start,end)],
            "truncated":trunc_c or trunc_p or trunc_i}
