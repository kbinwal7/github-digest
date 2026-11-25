from src.github.client import GitHubClient
from src.models.github_data import (
    normalize_commit,
    normalize_pull_request,
    normalize_issue
)
import json
from datetime import datetime

def main():
    client = GitHubClient()

    print(f"Collecting data from {client.owner}/{client.repo} ...")

    # Fetch raw data
    raw_commits = client.get_commits(per_page=30)
    raw_prs = client.get_pull_requests(per_page=20)
    raw_issues = client.get_issues(per_page=30)

    # Normalize
    commits = [normalize_commit(c) for c in raw_commits]
    pull_requests = [normalize_pull_request(pr) for pr in raw_prs]

    issues = []
    for raw in raw_issues:
        issue = normalize_issue(raw)
        if issue is not None:
            issues.append(issue)

    # Build the final structure
    data = {
        "repository": f"{client.owner}/{client.repo}",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "statistics": {
            "commits": len(commits),
            "pull_requests": len(pull_requests),
            "issues": len(issues)
        },
        "commits": [c.model_dump() for c in commits],
        "pull_requests": [pr.model_dump() for pr in pull_requests],
        "issues": [i.model_dump() for i in issues]
    }

    # Save to file
    with open("sample_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\nSuccessfully saved sample_data.json")
    print(f"  Commits        : {len(commits)}")
    print(f"  Pull Requests  : {len(pull_requests)}")
    print(f"  Issues         : {len(issues)}")
    print("\nYou can open sample_data.json to inspect the clean data.")

if __name__ == "__main__":
    main()