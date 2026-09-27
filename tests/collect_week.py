import argparse
import json
from datetime import datetime
from src.github.client import GitHubClient
from src.models.github_data import (
    normalize_commit,
    normalize_pull_request,
    normalize_issue
)
from src.utils.dates import parse_date, is_within_range

def collect_week(start_date: str, end_date: str):
    client = GitHubClient()
    start = parse_date(start_date)
    end = parse_date(end_date)

    print(f"Collecting activity for {client.owner}/{client.repo}")
    print(f"Week: {start_date} → {end_date}")
    print("-" * 50)

    # --- Commits (GitHub supports since/until) ---
    # We add one day to 'until' because the API is exclusive on the end
    until_for_api = (end + timedelta(days=1)).strftime("%Y-%m-%d")
    raw_commits = client.get_commits(since=start_date, until=until_for_api)
    commits = [normalize_commit(c) for c in raw_commits]

    # --- Pull Requests (filter in Python) ---
    raw_prs = client.get_pull_requests(per_page=100)
    pull_requests = []
    for raw in raw_prs:
        # We use updated_at or created_at / merged_at
        dates_to_check = [raw["created_at"], raw.get("merged_at"), raw["updated_at"]]
        if any(d and is_within_range(d, start, end) for d in dates_to_check):
            pull_requests.append(normalize_pull_request(raw))

    # --- Issues (filter in Python + remove PRs) ---
    raw_issues = client.get_issues(per_page=100)
    issues = []
    for raw in raw_issues:
        issue = normalize_issue(raw)
        if issue is None:
            continue
        dates_to_check = [raw["created_at"], raw.get("closed_at"), raw["updated_at"]]
        if any(d and is_within_range(d, start, end) for d in dates_to_check):
            issues.append(issue)

    # Build final structure
    data = {
        "repository": f"{client.owner}/{client.repo}",
        "week_start": start_date,
        "week_end": end_date,
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

    filename = f"week_{start_date}_to_{end_date}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved → {filename}")
    print(f"Commits        : {len(commits)}")
    print(f"Pull Requests  : {len(pull_requests)}")
    print(f"Issues         : {len(issues)}")

    return data

if __name__ == "__main__":
    from datetime import timedelta

    parser = argparse.ArgumentParser(description="Collect GitHub activity for a specific week")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    collect_week(args.start, args.end)