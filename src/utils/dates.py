from datetime import date, datetime
from typing import Any


def parse_github_datetime(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def filter_by_date_range(
    records: list[dict[str, Any]],
    date_field: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if (record_date := parse_github_datetime(record.get(date_field))) is not None
        and start_date <= record_date <= end_date
    ]