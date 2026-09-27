# GitHub Digest

A single-page Streamlit dashboard for exploring repository activity over a date range. Enter a repository and the dashboard fetches matching commits, pull requests, and issues from the GitHub API.

## Run locally

```powershell
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
streamlit run app.py
```

Enter a repository as `owner/repo` or paste its GitHub URL. Public repositories work without authentication. Add a personal access token to `.env` as `GITHUB_TOKEN` to access private repositories and increase the unauthenticated API rate limit. `GITHUB_OWNER` and `GITHUB_REPO` can optionally prefill the repository field.

The selected date window includes commit authored dates and pull request / issue creation dates. Up to 1,000 records per category are fetched; the dashboard warns when that cap is reached. It shows event totals, a combined overview, and dedicated commit, pull request, and issue lists with links back to GitHub.
