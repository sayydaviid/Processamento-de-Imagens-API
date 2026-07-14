from github_repo_stats.utils.text_utils import clean_text


def test_clean_text_removes_line_breaks_and_trims() -> None:
    assert clean_text("  linha 1\nlinha 2\r ") == "linha 1 linha 2"


def test_clean_text_handles_none() -> None:
    assert clean_text(None) == ""
