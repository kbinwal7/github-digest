from datetime import date
import pytest
from app.services.github import parse_repository
from app.services.digest import normalize_issue, normalize_commit
from app.services.indexing import issue_payload, prepare_issues
from app.core.config import Settings

def test_parse_repository_forms():
    assert parse_repository("octo-org/project")==("octo-org","project")
    assert parse_repository("https://github.com/octo-org/project.git/")==("octo-org","project")

@pytest.mark.parametrize("value",["","owner","https://example.com/a/b","a/b/c"])
def test_invalid_repository(value):
    with pytest.raises(ValueError): parse_repository(value)

def test_normalize_issue_skips_pull_requests():
    assert normalize_issue({"pull_request":{},"number":1}) is None

def test_normalize_commit_handles_missing_login():
    item=normalize_commit({"sha":"abcdef123","commit":{"message":"fix\nbody","author":{"name":"A","date":"2026-01-01T00:00:00Z"}}})
    assert item["sha"]=="abcdef1" and item["message"]=="fix"

def test_issue_payload_filters_and_truncates():
    settings=Settings(issue_text_max_chars=10)
    raw={"number":3,"title":"An issue title","body":"long body","state":"open","created_at":"2026-01-01T00:00:00Z","labels":[{"name":"bug"}]}
    result=issue_payload(raw,"o/r",settings)
    assert result["id"]=="o/r#3" and len(result["text"])==10
    assert issue_payload({**raw,"state":"closed"},"o/r",settings) is None
    assert issue_payload({**raw,"pull_request":{}},"o/r",settings) is None
