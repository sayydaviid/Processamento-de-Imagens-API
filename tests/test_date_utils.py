from github_repo_stats.utils.date_utils import parse_iso_date, unix_timestamp_to_date


def test_parse_iso_date_from_github_format() -> None:
    parsed = parse_iso_date("2026-07-14T12:30:00Z")
    assert parsed is not None
    assert parsed.isoformat() == "2026-07-14T12:30:00+00:00"


def test_parse_iso_date_returns_none_for_invalid_value() -> None:
    assert parse_iso_date("data-invalida") is None


def test_unix_timestamp_to_date() -> None:
    assert unix_timestamp_to_date(0) == "1970-01-01"
