import json
from typing import Any

import pytest

from github_repo_stats.api.github_client import GitHubClient
from github_repo_stats.exceptions import GitHubRateLimitError


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any,
        links: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        url: str = "https://api.github.com/test",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.links = links or {}
        self.headers = headers or {}
        self.url = url
        self.reason = "reason"
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self) -> Any:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, params=None, timeout=None) -> FakeResponse:
        self.calls.append({"method": method, "url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)

    def close(self) -> None:
        pass


def test_paginate_collects_all_pages(monkeypatch) -> None:
    monkeypatch.setattr("github_repo_stats.api.github_client.time.sleep", lambda _: None)
    first = FakeResponse(200, [{"id": 1}], links={"next": {"url": "https://api.github.com/page-2"}})
    second = FakeResponse(200, [{"id": 2}])
    client = GitHubClient(timeout=1, max_retries=0, sleep_between_requests=0)
    fake_session = FakeSession([first, second])
    client.session = fake_session  # type: ignore[assignment]

    rows = client.paginate("/items")

    assert rows == [{"id": 1}, {"id": 2}]
    assert fake_session.calls[0]["params"]["per_page"] == 100
    assert fake_session.calls[1]["params"] is None


def test_rate_limit_error_is_specific(monkeypatch) -> None:
    monkeypatch.setattr("github_repo_stats.api.github_client.time.sleep", lambda _: None)
    response = FakeResponse(
        403,
        {"message": "API rate limit exceeded"},
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1784059200"},
    )
    client = GitHubClient(timeout=1, max_retries=0, sleep_between_requests=0)
    client.session = FakeSession([response])  # type: ignore[assignment]

    with pytest.raises(GitHubRateLimitError):
        client.get("/rate-limited")
