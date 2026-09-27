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


st.set_page_config(
    page_title="GitHub Digest",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root { --ink: #e8edf5; --muted: #8b98aa; --panel: #111a27; --line: #233144; --green: #75e0b2; }
      .stApp { background: #0b111a; color: var(--ink); font-family: "Segoe UI", sans-serif; }
      [data-testid="stHeader"] { background: rgba(11, 17, 26, .92); }
      .block-container { max-width: 1180px; padding-top: 2.1rem; padding-bottom: 4rem; }
      .topbar { display: flex; align-items: center; justify-content: space-between; padding-bottom: 1.2rem; border-bottom: 1px solid var(--line); margin-bottom: 2.8rem; }
      .brand { color: var(--ink); font: 500 0.82rem "Cascadia Code", Consolas, monospace; letter-spacing: .08em; }
      .brand-mark { color: var(--green); margin-right: .65rem; }
      .live-pill { color: var(--green); background: rgba(117, 224, 178, .08); border: 1px solid rgba(117, 224, 178, .18); border-radius: 99px; padding: .36rem .7rem; font: 500 .68rem "Cascadia Code", Consolas, monospace; letter-spacing: .08em; }
      .eyebrow { color: var(--green); font: 500 .72rem "Cascadia Code", Consolas, monospace; letter-spacing: .13em; text-transform: uppercase; margin-bottom: .65rem; }
      .subtitle { color: var(--muted); max-width: 640px; line-height: 1.7; margin: -.4rem 0 1.7rem; }
      h1, h2, h3 { color: var(--ink); letter-spacing: -.04em; }
      [data-testid="stForm"] { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 1.25rem 1.35rem .65rem; }
      [data-testid="stTextInput"] label, [data-testid="stDateInput"] label { color: #aab6c6; font: 500 .69rem "Cascadia Code", Consolas, monospace; letter-spacing: .09em; }
      [data-testid="stTextInput"] input, [data-testid="stDateInput"] input { background: #0c131e; border-color: #2a394d; border-radius: 8px; }
      .stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button { background: var(--green); border: 0; color: #0b111a; font-weight: 800; border-radius: 8px; min-height: 2.65rem; }
      [data-testid="stMetric"] { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.15rem; }
      [data-testid="stMetricLabel"] { color: var(--muted); font: 500 .68rem "Cascadia Code", Consolas, monospace; letter-spacing: .09em; }
      [data-testid="stMetricValue"] { color: var(--ink); }
      [data-testid="stTabs"] button { font: 500 .78rem "Cascadia Code", Consolas, monospace; }
      [data-testid="stTabs"] button[aria-selected="true"] { color: var(--green); }
      [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line); border-radius: 11px; background: rgba(17, 26, 39, .58); }
      .section-kicker { color: var(--muted); font: 500 .68rem "Cascadia Code", Consolas, monospace; letter-spacing: .035em; text-transform: uppercase; }
      .item-title { color: var(--ink); font-weight: 700; line-height: 1.5; }
      .item-meta { color: var(--muted); font: .74rem "Cascadia Code", Consolas, monospace; }
      .stLinkButton a { border-color: #31435a; color: var(--green); border-radius: 7px; }
      div[data-testid="stAlert"] { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="topbar"><div class="brand"><span class="brand-mark">[G]</span>GITHUB / DIGEST</div>'
    '<div class="live-pill">LIVE / DATA</div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="eyebrow">Repository intelligence / 01</div>', unsafe_allow_html=True)
st.title("Activity, at a glance.")
st.markdown(
    '<p class="subtitle">A focused view of the work happening in any GitHub repository. '
    'Choose a repo and a date window to pull its commits, pull requests, and issues.</p>',
    unsafe_allow_html=True,
)

default_repository = "/".join(
    value for value in (os.getenv("GITHUB_OWNER"), os.getenv("GITHUB_REPO")) if value
)
if "digest_repository" not in st.session_state:
    st.session_state.digest_repository = default_repository

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
            value=(date.today() - timedelta(days=6), date.today()),
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
        <div style="border:1px dashed #2a394d;border-radius:12px;padding:1.2rem 1.35rem;color:#8b98aa">
          <span style="color:#75e0b2;font-family:'DM Mono',monospace">READY WHEN YOU ARE</span><br>
          Run a digest to see repository activity here. Public repositories work without a token;
          add <code>GITHUB_TOKEN</code> for private repos or a higher API rate limit.
        </div>
        """,
        unsafe_allow_html=True,
    )
