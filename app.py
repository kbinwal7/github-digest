from datetime import date, datetime, time, timedelta, timezone
from html import escape
import os
from typing import Any, Callable

import httpx
import streamlit as st

from src.github.client import GitHubClient, parse_repository
from src.models.github_data import (
    normalize_commit,
    normalize_issue,
    normalize_pull_request,
)
from src.utils.dates import filter_by_date_range, parse_github_datetime

# --- RAG / vector search stack (feature 2: AI Issue Matchmaker) ---------
try:
    from src.vector_db.client import IssueVectorStore
    from src.analysis.rag_engine import ContributionRAGEngine
    from src.models.issue_schema import VectorIssuePayload

    RAG_AVAILABLE = True
    RAG_IMPORT_ERROR = None
except Exception as _rag_import_error:  # pragma: no cover - defensive import guard
    RAG_AVAILABLE = False
    RAG_IMPORT_ERROR = _rag_import_error


st.set_page_config(
    page_title="GitHub Digest",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --bg: #090d12;
        --bg-raised: #0d131a;
        --panel: #10171f;
        --panel-hover: #131c25;
        --line: #1e2a35;
        --line-strong: #2a3947;
        --ink: #e6edf3;
        --ink-soft: #c4ced8;
        --muted: #7d8a98;
        --muted-strong: #9aa7b5;
        --green: #70d6a3;
        --green-soft: rgba(112, 214, 163, .09);
        --violet: #ad9cff;
        --violet-soft: rgba(173, 156, 255, .08);
        --mono: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
        --sans: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      html, body, [class*="css"] {
        font-family: var(--sans);
        font-size: 1.05rem;
      }

      .stApp {
        background:
          radial-gradient(circle at 50% -10%, rgba(112, 214, 163, .045), transparent 34rem),
          var(--bg);
        color: var(--ink);
      }

      [data-testid="stHeader"] {
        background: rgba(9, 13, 18, .88);
        border-bottom: 1px solid rgba(30, 42, 53, .65);
      }

      .block-container {
        max-width: 1200px;
        padding-top: 1.15rem;
        padding-bottom: 3.5rem;
      }

      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: .7rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.25rem;
        margin-top: .25rem;
      }

      .brand {
        color: var(--ink-soft);
        font: 600 0.95rem var(--mono);
        letter-spacing: .08em;
      }

      .brand-mark {
        color: var(--green);
        margin-right: .6rem;
      }

      .live-pill {
        color: var(--green);
        background: var(--green-soft);
        border: 1px solid rgba(112, 214, 163, .18);
        border-radius: 6px;
        padding: .35rem .65rem;
        font: 600 0.8rem var(--mono);
        letter-spacing: .08em;
      }

      .eyebrow {
        color: var(--green);
        font: 600 0.85rem var(--mono);
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: .35rem;
      }

      .subtitle {
        color: var(--muted);
        max-width: 750px;
        line-height: 1.7;
        margin: -.15rem 0 1rem;
        font-size: 1.05rem;
      }

      h1, h2, h3 {
        color: var(--ink);
        font-family: var(--sans);
        letter-spacing: -.035em;
      }

      h1 {
        font-weight: 650;
        font-size: 2.45rem;
      }

      h2, h3 {
        font-weight: 620;
        font-size: 1.6rem;
      }

      code, pre, .stCode {
        font-family: var(--mono);
      }

      [data-testid="stForm"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: .75rem .9rem .35rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, .14);
      }

      [data-testid="stTextInput"] label,
      [data-testid="stDateInput"] label,
      [data-testid="stNumberInput"] label {
        color: var(--muted-strong);
        font: 600 0.85rem var(--mono);
        letter-spacing: .09em;
      }

      [data-testid="stTextInput"] input,
      [data-testid="stDateInput"] input,
      [data-testid="stNumberInput"] input {
        background: #0b1117;
        border: 1px solid var(--line-strong);
        border-radius: 7px;
        color: var(--ink);
        font-family: var(--sans);
        font-size: 1.05rem;
        padding: 0.5rem 0.75rem;
      }

      [data-testid="stTextInput"] input:focus,
      [data-testid="stDateInput"] input:focus,
      [data-testid="stNumberInput"] input:focus {
        border-color: rgba(112, 214, 163, .55);
        box-shadow: 0 0 0 1px rgba(112, 214, 163, .18);
      }

      .stButton button,
      [data-testid="stFormSubmitButton"] button {
        border-radius: 7px;
        min-height: 2.75rem;
        font-family: var(--sans);
        font-weight: 650;
        font-size: 1.05rem;
        letter-spacing: -.01em;
      }

      .stButton button[kind="primary"],
      [data-testid="stFormSubmitButton"] button {
        background: var(--green);
        border: 1px solid var(--green);
        color: #07100b;
      }

      .stButton button[kind="primary"]:hover,
      [data-testid="stFormSubmitButton"] button:hover {
        background: #83dfb1;
        border-color: #83dfb1;
      }

      .stLinkButton a {
        background: transparent;
        border: 1px solid var(--line-strong);
        color: var(--green);
        border-radius: 7px;
        font-family: var(--mono);
        font-size: 0.9rem;
        font-weight: 600;
      }

      .stLinkButton a:hover {
        background: var(--green-soft);
        border-color: rgba(112, 214, 163, .35);
      }

      [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 9px;
        padding: 1rem 1.15rem;
      }

      [data-testid="stMetricLabel"] {
        color: var(--muted);
        font: 600 0.8rem var(--mono);
        letter-spacing: .08em;
      }

      [data-testid="stMetricValue"] {
        color: var(--ink);
        font-family: var(--mono);
        font-weight: 600;
        font-size: 1.6rem;
      }

      [data-testid="stTabs"] {
        margin-top: -.25rem;
      }

      [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: .2rem;
        border-bottom: 1px solid var(--line);
      }

      [data-testid="stTabs"] [data-baseweb="tab"] {
        padding: .8rem 1.1rem;
        color: var(--muted);
        font: 600 0.9rem var(--mono);
        letter-spacing: .02em;
      }

      [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: var(--green);
      }

      [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 9px;
        background: rgba(16, 23, 31, .72);
        transition: border-color .15s ease, background .15s ease;
      }

      [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #293846;
        background: var(--panel-hover);
      }

      .section-kicker {
        color: var(--muted);
        font: 600 0.8rem var(--mono);
        letter-spacing: .08em;
        text-transform: uppercase;
      }

      .item-title {
        color: var(--ink);
        font-family: var(--sans);
        font-size: 1.15rem;
        font-weight: 620;
        line-height: 1.45;
      }

      .item-meta {
        color: var(--muted);
        font: 0.85rem var(--mono);
        line-height: 1.6;
      }

      .feature-row {
        display: flex;
        gap: 1.15rem;
        margin-bottom: .9rem;
      }

      .feature-card {
        flex: 1;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: .8rem 1rem;
        background: rgba(16, 23, 31, .7);
      }

      .feature-card .tag {
        display: inline-block;
        font: 600 0.8rem var(--mono);
        letter-spacing: .08em;
        padding: .3rem .6rem;
        border-radius: 6px;
        margin-bottom: .65rem;
      }

      .feature-card.f1 .tag {
        color: var(--green);
        background: var(--green-soft);
        border: 1px solid rgba(112, 214, 163, .16);
      }

      .feature-card.f2 .tag {
        color: var(--violet);
        background: var(--violet-soft);
        border: 1px solid rgba(173, 156, 255, .18);
      }

      .feature-card .f-title {
        color: var(--ink-soft);
        font-weight: 600;
        font-size: 1rem;
        line-height: 1.35;
        margin-bottom: .15rem;
      }

      .feature-card .f-desc {
        color: var(--muted);
        font-size: .9rem;
        line-height: 1.4;
      }

      .match-score {
        color: var(--violet);
        font: 600 0.78rem var(--mono);
      }

      .advice-panel {
        border: 1px solid var(--line);
        border-radius: 9px;
        padding: 1.2rem 1.35rem;
        background: var(--violet-soft);
        color: var(--ink-soft);
        line-height: 1.7;
        font-size: 1.05rem;
      }

      div[data-testid="stAlert"] {
        border-radius: 8px;
        font-size: 1rem;
      }

      .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted);
        font-size: 0.9rem;
      }

      hr {
        border-color: var(--line);
      }

      @media (max-width: 800px) {
        .feature-row {
          flex-direction: column;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="topbar"><div class="brand"><span class="brand-mark"></span></div>'
    '<div class="live-pill"></div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="eyebrow">[G] GITHUB DIGEST</div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Repository intelligence / 01</div>', unsafe_allow_html=True)
st.title("Activity, at a glance.")
st.markdown(
    '<p class="subtitle">Two ways to work with any GitHub repository: pull a digest of recent '
    'commits, pull requests, and issues — or ask the AI matchmaker to surface issues worth '
    'your time and tell you why.</p>',
    unsafe_allow_html=True,
)

# --- Feature highlight row (purely visual, keeps both features top of mind) ---
st.markdown(
    """
    <div class="feature-row">
      <div class="feature-card f1">
        <span class="tag">Activity Digest</span>
        <div class="f-title">Fetch and browse commits, pull requests, and issues for any repo across a date window.</div>
        <div class="f-desc"></div>
      </div>
      <div class="feature-card f2">
        <span class="tag">AI Issue Matchmaker</span>
        <div class="f-title">Describe what you want to work on — get vector-matched issues plus AI-written advice on how to contribute.</div>
        <div class="f-desc"></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

digest_tab, matchmaker_tab = st.tabs(["ACTIVITY DIGEST", "AI ISSUE MATCHMAKER"])

default_repository = "/".join(
    value for value in (os.getenv("GITHUB_OWNER"), os.getenv("GITHUB_REPO")) if value
)
if "digest_repository" not in st.session_state:
    st.session_state.digest_repository = default_repository


@st.cache_resource
def load_rag_pipeline():
    return IssueVectorStore(), ContributionRAGEngine()


def render_item(kind: str, item: dict[str, Any]) -> None:
    if kind == "commit":
        title = item["message"]
        identifier = item["sha"]
        date_value = item["date"]
        state = "commit"
    else:
        identifier = f"#{item['number']}"
        title = item["title"]
        date_value = item["created_at"]
        state = item["state"]

    with st.container(border=True):
        title_col, link_col = st.columns([1, 0.22], vertical_alignment="center")
        with title_col:
            st.markdown(
                f'<div class="item-title">{escape(title)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="item-meta">{escape(identifier)} &nbsp;·&nbsp; '
                f'{escape(item["author"])} &nbsp;·&nbsp; '
                f'{escape(date_value[:10])} &nbsp;·&nbsp; {escape(state)}</div>',
                unsafe_allow_html=True,
            )
            if item.get("labels"):
                st.caption("  /  ".join(item["labels"]))
        with link_col:
            st.link_button("View", item["url"], use_container_width=True)


# =========================================================================
# FEATURE 01 — ACTIVITY DIGEST
# =========================================================================
with digest_tab:
    with st.form("activity_filters"):
        repo_col, date_col, button_col = st.columns([1.25, 1.0, 0.58], vertical_alignment="bottom")
        with repo_col:
            repository_input = st.text_input(
                "REPOSITORY",
                value=st.session_state.digest_repository,
                placeholder="owner/repository",
                help="Enter owner/repo, or paste a github.com repository URL.",
            )
        with date_col:
            date_selection = st.date_input(
                "DATE WINDOW",
                value=(date.today() - timedelta(days=1), date.today()),
                max_value=date.today(),
                format="YYYY-MM-DD",
                help="Commits use their authored date; pull requests and issues use their creation date.",
            )
        with button_col:
            submitted = st.form_submit_button("Run digest", type="primary", use_container_width=True)

    st.caption("Date window applies to commit authored dates and issue / pull request creation dates.")

    if submitted:
        st.session_state.pop("digest_results", None)
        if not repository_input.strip():
            st.error("Enter a repository to run the digest.")
        elif not isinstance(date_selection, (tuple, list)) or len(date_selection) != 2:
            st.error("Select both a start date and an end date.")
        else:
            start_date, end_date = date_selection
            if start_date > end_date:
                st.error("The start date must be on or before the end date.")
            else:
                try:
                    owner, repo = parse_repository(repository_input)
                    client = GitHubClient(f"{owner}/{repo}")
                    window_start = datetime.combine(start_date, time.min, timezone.utc).isoformat()
                    window_end = datetime.combine(end_date, time.max, timezone.utc).isoformat()
                    page_size = 100
                    max_pages = 10
                    truncated_categories: list[str] = []

                    def fetch_pages(
                        fetch_page: Callable[[int], list[dict[str, Any]]],
                        date_field: str,
                    ) -> list[dict[str, Any]]:
                        records: list[dict[str, Any]] = []
                        for page in range(1, max_pages + 1):
                            page_records = fetch_page(page)
                            records.extend(page_records)
                            page_dates = [
                                record_date
                                for record in page_records
                                if (
                                    record_date := parse_github_datetime(
                                        record["commit"]["author"]["date"]
                                        if date_field == "commit.date"
                                        else record.get(date_field)
                                    )
                                )
                                is not None
                            ]
                            if not page_records or len(page_records) < page_size:
                                break
                            if page_dates and min(page_dates) < start_date:
                                break
                            if page == max_pages:
                                truncated_categories.append(date_field)
                        return records

                    with st.spinner(f"Fetching activity for {owner}/{repo}…"):
                        raw_commits = fetch_pages(
                            lambda page: client.get_commits(
                                per_page=page_size,
                                page=page,
                                since=window_start,
                                until=window_end,
                            ),
                            "commit.date",
                        )
                        raw_pull_requests = fetch_pages(
                            lambda page: client.get_pull_requests(per_page=page_size, page=page),
                            "created_at",
                        )
                        raw_issues = fetch_pages(
                            lambda page: client.get_issues(per_page=page_size, page=page),
                            "created_at",
                        )

                    commits = [
                        normalize_commit(record).model_dump()
                        for record in raw_commits
                    ]
                    pull_requests = [
                        normalize_pull_request(record).model_dump()
                        for record in raw_pull_requests
                    ]
                    issues = [
                        issue.model_dump()
                        for record in raw_issues
                        if (issue := normalize_issue(record)) is not None
                    ]
                    results = {
                        "repository": f"{owner}/{repo}",
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "commits": filter_by_date_range(commits, "date", start_date, end_date),
                        "pull_requests": filter_by_date_range(
                            pull_requests, "created_at", start_date, end_date
                        ),
                        "issues": filter_by_date_range(issues, "created_at", start_date, end_date),
                        "truncated": bool(truncated_categories),
                    }
                    st.session_state.digest_results = results
                    st.session_state.digest_repository = f"{owner}/{repo}"

                    # --- Feed feature 2: index open issues (not PRs) for vector search ---
                    if RAG_AVAILABLE:
                        try:
                            vector_store, _ = load_rag_pipeline()
                            repo_slug = f"{owner}/{repo}"

                            # REQ 4 — skip re-indexing a repo that's already in Qdrant
                            if not vector_store.is_repo_indexed(repo_slug):
                                st.info(f"Indexing open issues for {repo_slug}...")

                                open_issue_records = [
                                    record for record in raw_issues if "pull_request" not in record
                                ]

                                # REQ 1 & 2 — from_github_issue filters out stale / non-issue
                                # records itself and returns None for anything that shouldn't
                                # be indexed, so only truthy parses make it into the batch.
                                payloads = []
                                for record in open_issue_records:
                                    parsed = VectorIssuePayload.from_github_issue(record, repo_slug)
                                    if parsed:
                                        payloads.append(parsed.model_dump())

                                # REQ 3 — batch embed & upsert
                                if payloads:
                                    vector_store.upsert_issues(payloads)
                                    st.success(f"Indexed {len(payloads)} fresh open issues!")
                                else:
                                    st.warning("No recent open issues found meeting criteria.")

                                st.session_state.matchmaker_indexed_repo = repo_slug
                                st.session_state.matchmaker_indexed_count = len(payloads)
                            else:
                                st.info(f"Loaded cached index for {repo_slug} from Qdrant Cloud.")
                                st.session_state.matchmaker_indexed_repo = repo_slug
                                st.session_state.matchmaker_indexed_count = None
                        except Exception as index_error:
                            st.session_state.matchmaker_index_error = str(index_error)

                except ValueError as error:
                    st.error(str(error))
                except httpx.HTTPStatusError as error:
                    status_code = error.response.status_code
                    if status_code == 404:
                        st.error("Repository not found, or it is private. Check the name and your GitHub token.")
                    elif status_code == 401:
                        st.error("GitHub rejected the token. Check GITHUB_TOKEN and try again.")
                    elif status_code == 403 and error.response.headers.get("X-RateLimit-Remaining") == "0":
                        st.error("GitHub API rate limit reached. Add a personal access token as GITHUB_TOKEN and retry.")
                    else:
                        st.error(f"GitHub returned HTTP {status_code}: {error.response.text[:300]}")
                except httpx.HTTPError as error:
                    st.error(f"Could not reach the GitHub API: {error}")

    if RAG_AVAILABLE and st.session_state.get("matchmaker_indexed_repo"):
        st.caption(
            f"AI Matchmaker is ready to search {st.session_state.matchmaker_indexed_repo} → check the second tab."
        )
    if st.session_state.get("matchmaker_index_error"):
        st.warning(f"Digest ran, but indexing for the matchmaker failed: {st.session_state.matchmaker_index_error}")

    results = st.session_state.get("digest_results")
    if results:
        st.markdown("")
        meta_col, time_col = st.columns([1.5, 0.5])
        with meta_col:
            st.markdown(
                f'<div class="section-kicker">RESULTS &nbsp; / &nbsp; '
                f'{escape(results["repository"])} &nbsp; / &nbsp; '
                f'{escape(results["start_date"])} - {escape(results["end_date"])}</div>',
                unsafe_allow_html=True,
            )
        with time_col:
            st.markdown(
                f'<div class="section-kicker" style="text-align:right">UPDATED '
                f'{escape(results["collected_at"][11:19])} UTC</div>',
                unsafe_allow_html=True,
            )

        commit_count = len(results["commits"])
        pr_count = len(results["pull_requests"])
        issue_count = len(results["issues"])
        metric_cols = st.columns(4)
        metric_cols[0].metric("TOTAL EVENTS", commit_count + pr_count + issue_count)
        metric_cols[1].metric("COMMITS", commit_count)
        metric_cols[2].metric("PULL REQUESTS", pr_count)
        metric_cols[3].metric("ISSUES", issue_count)

        if results["truncated"]:
            st.warning("A category reached the 1,000-result fetch limit. Narrow the date window to include all matching activity.")

        overview_tab, commit_tab, pr_tab, issue_tab = st.tabs(
            ["Overview", "Commits", "Pull requests", "Issues"]
        )
        collections = [
            ("commit", results["commits"]),
            ("pull request", results["pull_requests"]),
            ("issue", results["issues"]),
        ]
        with overview_tab:
            st.markdown('<div class="section-kicker">LATEST ACTIVITY</div>', unsafe_allow_html=True)
            latest = [
                (kind, item)
                for kind, items in collections
                for item in items
            ]
            latest.sort(
                key=lambda entry: parse_github_datetime(
                    entry[1].get("date") or entry[1].get("created_at")
                )
                or date.min,
                reverse=True,
            )
            if latest:
                for kind, item in latest[:15]:
                    render_item(kind, item)
            else:
                st.info("No activity found in this date window. Try a wider range.")

        with commit_tab:
            st.markdown('<div class="section-kicker">COMMITS IN WINDOW</div>', unsafe_allow_html=True)
            if results["commits"]:
                for item in results["commits"][:50]:
                    render_item("commit", item)
                if commit_count > 50:
                    st.caption(f"Showing the latest 50 of {commit_count:,} commits.")
            else:
                st.info("No commits found in this date window.")

        with pr_tab:
            st.markdown('<div class="section-kicker">PULL REQUESTS IN WINDOW</div>', unsafe_allow_html=True)
            if results["pull_requests"]:
                for item in results["pull_requests"][:50]:
                    render_item("pull request", item)
                if pr_count > 50:
                    st.caption(f"Showing the latest 50 of {pr_count:,} pull requests.")
            else:
                st.info("No pull requests found in this date window.")

        with issue_tab:
            st.markdown('<div class="section-kicker">ISSUES IN WINDOW</div>', unsafe_allow_html=True)
            if results["issues"]:
                for item in results["issues"][:50]:
                    render_item("issue", item)
                if issue_count > 50:
                    st.caption(f"Showing the latest 50 of {issue_count:,} issues.")
            else:
                st.info("No issues found in this date window.")
    else:
        st.markdown(
            """
            <div style="border:1px dashed #2a394d;border-radius:12px;padding:1.2rem 1.35rem;color:#8b98aa;font-size:1.05rem;">
              <span style="color:#75e0b2;font-family:'DM Mono',monospace">READY WHEN YOU ARE</span><br>
              Run a digest to see repository activity here. Public repositories work without a token;
              add <code>GITHUB_TOKEN</code> for private repos or a higher API rate limit.
              Running a digest also indexes that repo's open issues for the AI Matchmaker tab.
            </div>
            """,
            unsafe_allow_html=True,
        )

# =========================================================================
# FEATURE 02 — AI ISSUE MATCHMAKER
# =========================================================================
with matchmaker_tab:
    st.markdown('<div class="section-kicker">VECTOR SEARCH + AI ADVICE</div>', unsafe_allow_html=True)
    st.markdown("### Find an issue worth your time")

    if not RAG_AVAILABLE:
        st.error(
            "The matchmaker backend isn't wired up yet (couldn't import the vector store / RAG "
            f"engine modules: {RAG_IMPORT_ERROR}). The activity digest still works normally."
        )
    else:
        indexed_repo = st.session_state.get("matchmaker_indexed_repo")
        if indexed_repo:
            st.markdown(
                f'<div class="item-meta">Searching against indexed issues from '
                f'<span style="color:var(--green)">{escape(indexed_repo)}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Run a digest in the first tab to index a repo's open issues, then search here.")

        search_col, limit_col = st.columns([3, 1], vertical_alignment="bottom")
        with search_col:
            user_search = st.text_input(
                "WHAT DO YOU WANT TO WORK ON?",
                placeholder="e.g. beginner python async bugs, doc updates, TypeScript refactoring",
                label_visibility="visible",
            )
        with limit_col:
            match_limit = st.number_input("MATCHES", min_value=1, max_value=10, value=3, step=1)

        run_search = st.button("Find matching issues", type="primary", use_container_width=False)

        if run_search and user_search.strip():
            if not indexed_repo:
                st.warning("No issues indexed yet — run a digest first so there's something to search.")
            else:
                with st.spinner("Searching the vector index and drafting advice…"):
                    try:
                        vector_store, rag_engine = load_rag_pipeline()
                        matches = vector_store.search_similar_issues(
                            query=user_search,
                            repo_filter=indexed_repo,
                            limit=int(match_limit),
                        )
                        advice = rag_engine.generate_recommendation(
                            user_query=user_search,
                            retrieved_points=matches,
                        )
                        st.session_state.matchmaker_matches = matches
                        st.session_state.matchmaker_advice = advice
                    except Exception as search_error:
                        st.error(f"Search failed: {search_error}")
                        st.session_state.pop("matchmaker_matches", None)
                        st.session_state.pop("matchmaker_advice", None)

        matches = st.session_state.get("matchmaker_matches")
        advice = st.session_state.get("matchmaker_advice")

        if matches:
            st.markdown('<div class="section-kicker" style="margin-top:1.4rem">MATCHED ISSUES</div>', unsafe_allow_html=True)
            for match in matches:
                payload = getattr(match, "payload", None) or (match.get("payload") if isinstance(match, dict) else match)
                score = getattr(match, "score", None) or (match.get("score") if isinstance(match, dict) else None)
                title = (payload or {}).get("title", "Untitled issue")
                url = (payload or {}).get("url", "#")
                labels = (payload or {}).get("labels", [])
                with st.container(border=True):
                    top_col, score_col = st.columns([1, 0.3], vertical_alignment="center")
                    with top_col:
                        st.markdown(f'<div class="item-title">{escape(title)}</div>', unsafe_allow_html=True)
                        if labels:
                            st.caption("  /  ".join(labels))
                    with score_col:
                        if score is not None:
                            st.markdown(f'<div class="match-score" style="text-align:right">MATCH {score:.2f}</div>', unsafe_allow_html=True)
                        st.link_button("View issue", url, use_container_width=True)

        if advice:
            st.markdown('<div class="section-kicker" style="margin-top:1.4rem">RECOMMENDATION</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="advice-panel">{advice}</div>', unsafe_allow_html=True)