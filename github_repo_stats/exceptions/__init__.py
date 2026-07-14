"""Exceções específicas da aplicação."""

from github_repo_stats.exceptions.github_api_error import (
    ConfigurationError,
    ExportError,
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
)

__all__ = [
    "ConfigurationError",
    "ExportError",
    "GitHubApiError",
    "GitHubAuthenticationError",
    "GitHubRateLimitError",
]
