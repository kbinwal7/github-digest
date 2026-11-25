from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

# Issues older than this are treated as stale and skipped when indexing -
# a two-year-old untouched issue isn't a great "come contribute" match.
STALE_AFTER_DAYS = 730


class VectorIssuePayload(BaseModel):
    """Shape of a single issue as it goes into the vector store.

    `id` is a stable string key (repo#number). `text` is what gets embedded.
    `metadata` is everything else we want back out of Qdrant at query time
    (it gets flattened into the point's payload alongside `text`).
    """

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_github_issue(cls, record: dict[str, Any], repo_name: str) -> Optional["VectorIssuePayload"]:
        # The GitHub Issues API returns pull requests too - they carry a
        # "pull_request" key. We only want real issues here.
        if "pull_request" in record:
            return None

        # Only index issues that are actually open and available to work on.
        if record.get("state") != "open":
            return None

        title = (record.get("title") or "").strip()
        if not title:
            return None
        body = (record.get("body") or "").strip()

        created_at = record.get("created_at")
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - created > timedelta(days=STALE_AFTER_DAYS):
                    return None
            except ValueError:
                pass  # unparseable date - don't let that block indexing

        number = record.get("number")
        labels = [
            label["name"] if isinstance(label, dict) else str(label)
            for label in record.get("labels", [])
        ]

        return cls(
            id=f"{repo_name}#{number}",
            # Keep the embedded text bounded so a huge issue body doesn't
            # blow up the embedding request.
            text=f"{title}\n\n{body}"[:8000],
            metadata={
                "repo": repo_name,
                "number": number,
                "title": title,
                "url": record.get("html_url", ""),
                "labels": labels,
                "state": record.get("state", "open"),
                "created_at": created_at,
            },
        )

    @staticmethod
    def stable_point_id(issue_id: str) -> int:
        """Deterministic integer ID for Qdrant, stable across process restarts.

        Python's builtin hash() is randomized per-process (PYTHONHASHSEED),
        so the same issue string would get a different point ID on every
        run of the app - that silently breaks de-duplication and makes
        "update this issue's vector" impossible. Hash digests don't have
        that problem.
        """
        digest = hashlib.sha256(issue_id.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)