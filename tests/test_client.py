from src.github.client import GitHubClient
from src.models.github_data import (
    normalize_commit,
    normalize_pull_request,
    normalize_issue
)
import json

client = GitHubClient()

print(f"Repository: {client.owner}/{client.repo}")
print("=" * 60)

# Normalize commits
raw_commits = client.get_commits(per_page=10)
commits = [normalize_commit(c) for c in raw_commits]

print(f"\nNormalized COMMITS ({len(commits)})")
for c in commits[:3]:
    print(c.model_dump())

# Normalize pull requests
raw_prs = client.get_pull_requests(per_page=10)
prs = [normalize_pull_request(pr) for pr in raw_prs]

print(f"\nNormalized PULL REQUESTS ({len(prs)})")
for pr in prs[:3]:
    print(pr.model_dump())

# Normalize issues (PRs filtered out)
raw_issues = client.get_issues(per_page=20)
issues = [normalize_issue(i) for i in raw_issues]
issues = [i for i in issues if i is not None]  # remove None values

print(f"\nNormalized ISSUES ({len(issues)})")
for issue in issues[:3]:
    print(issue.model_dump())