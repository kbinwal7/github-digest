import re
from datetime import date, datetime, time, timezone
from typing import Any
import httpx

_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

def parse_repository(value: str) -> tuple[str, str]:
    value = value.strip().rstrip("/")
    if value.startswith("https://github.com/"):
        value = value[len("https://github.com/"):]
    value = value.removesuffix(".git")
    if not _REPO.fullmatch(value):
        raise ValueError("Enter a repository as owner/repo or a GitHub repository URL.")
    return tuple(value.split("/", 1))

def parse_date(value: str) -> date:
    return date.fromisoformat(value)

def in_window(value: str | None, start: date, end: date) -> bool:
    if not value: return False
    try: return start <= datetime.fromisoformat(value.replace("Z", "+00:00")).date() <= end
    except ValueError: return False

class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str, headers: dict | None = None):
        self.status_code, self.message, self.headers = status_code, message, headers or {}
        super().__init__(message)

class GitHubClient:
    def __init__(self, token: str | None = None, timeout: float = 25):
        self.token, self.timeout = token, timeout

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict) -> list[dict[str, Any]]:
        response = await client.get(path, params=params)
        if response.is_error:
            try: detail = response.json().get("message", response.text[:300])
            except Exception: detail = response.text[:300]
            raise GitHubAPIError(response.status_code, detail, dict(response.headers))
        data = response.json()
        return data if isinstance(data, list) else [data]

    async def fetch_pages(self, owner: str, repo: str, resource: str, *,
                          since: str | None = None, until: str | None = None,
                          state: str = "all", max_pages: int = 10) -> tuple[list[dict], bool]:
        headers = {"Accept":"application/vnd.github+json", "X-GitHub-Api-Version":"2022-11-28"}
        if self.token: headers["Authorization"] = f"Bearer {self.token}"
        params = {"per_page":100}
        if resource in ("pulls", "issues"):
            params.update({"state":state,"sort":"created","direction":"desc"})
        if since: params["since"] = since
        if until: params["until"] = until
        path = f"https://api.github.com/repos/{owner}/{repo}/{resource}"
        records=[]
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout) as client:
            for page in range(1, max_pages+1):
                page_data = await self._get(client, path, {**params, "page":page})
                records.extend(page_data)
                if len(page_data) < 100: return records, False
        return records, True

    async def repository_status(self, owner: str, repo: str) -> dict:
        headers={"Accept":"application/vnd.github+json"}
        if self.token: headers["Authorization"]=f"Bearer {self.token}"
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout) as client:
            data=(await self._get(client, f"https://api.github.com/repos/{owner}/{repo}", {}))[0]
        return {"full_name":data.get("full_name"),"private":data.get("private"),
                "default_branch":data.get("default_branch"),"open_issues_count":data.get("open_issues_count"),
                "html_url":data.get("html_url")}
