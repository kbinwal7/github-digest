import os
from dotenv import load_dotenv
import httpx

load_dotenv()

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo=os.getenv("GITHUB_REPO")
        self.base_url="https://api.github.com"
        self.headers={
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"            
        }
        
    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        
    def get_commits(self, per_page: int = 20):
        path = f"/repos/{self.owner}/{self.repo}/commits"
        params = {"per_page": per_page}
        return self._get(path, params=params)
    
    def get_pull_requests(self, state: str = "all", per_page: int = 20):
        """
        state can be: open, closed, or all
        """
        path = f"/repos/{self.owner}/{self.repo}/pulls"
        params = {
            "state": state,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        return self._get(path, params=params)
    
    
    def get_issues(self, state: str = "all", per_page: int = 20):
        """
        Important: GitHub's /issues endpoint also returns pull requests.
        We will filter them out later.
        """
        path = f"/repos/{self.owner}/{self.repo}/issues"
        params = {
            "state": state,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        return self._get(path, params=params)
        
