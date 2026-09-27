import unittest
from datetime import date
from unittest.mock import patch

from src.github.client import GitHubClient, parse_repository
from src.utils.dates import filter_by_date_range, parse_github_datetime


class RepositoryParsingTests(unittest.TestCase):
    def test_parses_repository_name_and_github_url(self):
        self.assertEqual(parse_repository("octo-org/project"), ("octo-org", "project"))
        self.assertEqual(
            parse_repository("https://github.com/octo-org/project.git/"),
            ("octo-org", "project"),
        )

    def test_rejects_invalid_repository_input(self):
        for value in ("", "owner", "https://example.com/owner/repo", "owner/repo/extra"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_repository(value)

    def test_client_uses_repository_and_optional_token(self):
        client = GitHubClient("octo-org/project", token="test-token")
        self.assertEqual(client.headers["Authorization"], "Bearer test-token")

        with patch.object(client, "_get", return_value=[]) as request:
            client.get_commits(
                per_page=100,
                page=2,
                since="2026-09-01T00:00:00+00:00",
                until="2026-09-02T23:59:59+00:00",
            )

        request.assert_called_once_with(
            "/repos/octo-org/project/commits",
            params={
                "per_page": 100,
                "page": 2,
                "since": "2026-09-01T00:00:00+00:00",
                "until": "2026-09-02T23:59:59+00:00",
            },
        )

        public_client = GitHubClient("octo-org/project", token="")
        self.assertNotIn("Authorization", public_client.headers)


class DateRangeTests(unittest.TestCase):
    def test_filters_inclusive_date_range(self):
        records = [
            {"created_at": "2026-09-01T00:00:00Z"},
            {"created_at": "2026-09-02T23:59:59Z"},
            {"created_at": "2026-09-03T00:00:00Z"},
            {"created_at": None},
        ]

        self.assertEqual(
            filter_by_date_range(
                records,
                "created_at",
                date(2026, 9, 1),
                date(2026, 9, 2),
            ),
            records[:2],
        )

    def test_parses_utc_github_timestamp(self):
        self.assertEqual(
            parse_github_datetime("2026-09-27T07:26:06Z"),
            date(2026, 9, 27),
        )


if __name__ == "__main__":
    unittest.main()
