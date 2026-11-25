from datetime import datetime, timezone, timedelta
from typing import Any
from app.core.config import Settings

def issue_payload(record: dict, repo_name: str, settings: Settings) -> dict | None:
    if "pull_request" in record or record.get("state") != "open": return None
    title=(record.get("title") or "").strip()
    if not title: return None
    created_at=record.get("created_at")
    if created_at:
        try:
            created=datetime.fromisoformat(created_at.replace("Z","+00:00"))
            if datetime.now(timezone.utc)-created > timedelta(days=settings.stale_after_days): return None
        except ValueError: pass
    labels=[x.get("name","") if isinstance(x,dict) else str(x) for x in record.get("labels",[])]
    number=record.get("number")
    return {"id":f"{repo_name}#{number}","text":f"{title}\n\n{(record.get('body') or '').strip()}"[:settings.issue_text_max_chars],
            "metadata":{"repo":repo_name,"number":number,"title":title,"url":record.get("html_url",""),
                        "labels":labels,"state":"open","created_at":created_at}}

def prepare_issues(records: list[dict], repo_name: str, settings: Settings) -> list[dict]:
    return [payload for record in records if (payload:=issue_payload(record,repo_name,settings))]
