import os
import re
from dotenv import load_dotenv
import httpx

load_dotenv()


_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_repository(value: str) -> tuple[str, str]:
    repository = value.strip().rstrip("/")
    if repository.startswith("https://github.com/"):
        repository = repository.removeprefix("https://github.com/")
    repository = repository.removesuffix(".git")
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Enter a GitHub repository as owner/repo or a github.com URL.")
    owner, repo = repository.split("/", maxsplit=1)
    return owner, repo


class GitHubClient:
    def __init__(self, repository: str | None = None, token: str | None = None):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        if repository is None:
            owner = os.getenv("GITHUB_OWNER")
            repo = os.getenv("GITHUB_REPO")
            if not owner or not repo:
                raise ValueError(
                    "Provide a repository or set GITHUB_OWNER and GITHUB_REPO."
                )
            self.owner, self.repo = parse_repository(f"{owner}/{repo}")
        else:
            self.owner, self.repo = parse_repository(repository)

        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    def get_commits(
        self,
        per_page: int = 20,
        page: int = 1,
        since: str | None = None,
        until: str | None = None,
    ):
        path = f"/repos/{self.owner}/{self.repo}/commits"
        params = {"per_page": per_page, "page": page}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._get(path, params=params)

    def get_pull_requests(
        self, state: str = "all", per_page: int = 20, page: int = 1
    ):
        path = f"/repos/{self.owner}/{self.repo}/pulls"
        params = {
            "state": state,
            "per_page": per_page,
            "page": page,
            "sort": "created",
            "direction": "desc"
        }
        return self._get(path, params=params)

    def get_issues(self, state: str = "all", per_page: int = 20, page: int = 1):
        path = f"/repos/{self.owner}/{self.repo}/issues"
        params = {
            "state": state,
            "per_page": per_page,
            "page": page,
            "sort": "created",
            "direction": "desc"
        }
        return self._get(path, params=params)
