"""Cliente HTTP responsável exclusivamente pela API do GitHub."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

import requests

from github_repo_stats.config import DEFAULT_API_VERSION
from github_repo_stats.exceptions import (
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
)


API_BASE_URL = "https://api.github.com"
TRANSIENT_STATUS_CODES = {500, 502, 503, 504}


class GitHubClient:
    """Cliente com sessão HTTP, paginação, timeout e tratamento de erros."""

    def __init__(
        self,
        token: Optional[str] = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout: float = 20.0,
        max_retries: int = 3,
        sleep_between_requests: float = 0.15,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.session = requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep_between_requests = sleep_between_requests
        self.logger = logger or logging.getLogger(__name__)

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-repo-stats",
            "X-GitHub-Api-Version": api_version,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        """Fecha a sessão HTTP."""

        self.session.close()

    def get(self, path_or_url: str, params: Optional[dict[str, Any]] = None, **kwargs: Any) -> Any:
        """Executa uma requisição GET e retorna o JSON decodificado."""

        url = self._build_url(path_or_url)
        return self.request("GET", url, params=params, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        retry_stats_202: bool = True,
        max_202_retries: int = 8,
    ) -> Any:
        """Executa uma requisição e trata os códigos HTTP relevantes.

        Alguns endpoints de estatísticas do GitHub retornam HTTP 202 enquanto
        os dados do Insights ainda estão sendo calculados. Nesses casos a
        aplicação tenta novamente algumas vezes antes de retornar ``None``.
        """

        attempts = max_202_retries if retry_stats_202 else 1
        for attempt in range(attempts):
            response = self._send_with_retries(method, url, params=params)

            if response.status_code == 202 and retry_stats_202:
                wait_seconds = 2 + attempt
                self.logger.info(
                    "GitHub ainda está calculando estatísticas. Nova tentativa em %ss.",
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            self._raise_for_status(response, operation=f"{method} {url}")
            return self._decode_json(response)

        self.logger.warning("A estatística não ficou pronta após as tentativas configuradas.")
        return None

    def paginate(self, path: str, params: Optional[dict[str, Any]] = None) -> list[Any]:
        """Percorre paginação por links ``next`` da API do GitHub."""

        request_params = dict(params or {})
        request_params.setdefault("per_page", 100)
        url: Optional[str] = self._build_url(path)
        results: list[Any] = []

        while url:
            response = self._send_with_retries("GET", url, params=request_params)
            self._raise_for_status(response, operation=f"paginação GET {url}")

            data = self._decode_json(response)
            if isinstance(data, list):
                results.extend(data)
            elif data is not None:
                results.append(data)

            url = response.links.get("next", {}).get("url")
            request_params = None

        return results

    def _send_with_retries(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        last_error: Optional[BaseException] = None

        for attempt in range(self.max_retries + 1):
            if self.sleep_between_requests:
                time.sleep(self.sleep_between_requests)

            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt)
                    continue
                raise GitHubApiError(
                    "Falha de comunicação com a API do GitHub. "
                    "Verifique a conexão com a internet e tente novamente."
                ) from exc

            if response.status_code in TRANSIENT_STATUS_CODES and attempt < self.max_retries:
                self.logger.warning(
                    "Erro temporário %s na API do GitHub. Tentando novamente.",
                    response.status_code,
                )
                self._sleep_before_retry(attempt)
                continue

            if response.status_code == 429 and attempt < self.max_retries:
                self._sleep_from_rate_headers(response, attempt)
                continue

            return response

        raise GitHubApiError("Falha inesperada ao executar requisição ao GitHub.") from last_error

    def _raise_for_status(self, response: requests.Response, operation: str) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return

        message = self._extract_error_message(response)
        url = self._safe_url(response)

        if status == 401:
            raise GitHubAuthenticationError(
                f"Falha de autenticação ao executar {operation}. "
                "Verifique se GITHUB_TOKEN está correto no arquivo .env."
            )

        if status == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            if remaining == "0":
                reset_text = self._format_rate_reset(reset)
                raise GitHubRateLimitError(
                    f"Limite de requisições do GitHub atingido ao executar {operation}. "
                    f"Tente novamente depois de {reset_text} ou configure GITHUB_TOKEN no .env."
                )
            raise GitHubApiError(
                f"Acesso negado pelo GitHub ao executar {operation}. "
                "Verifique as permissões do token e o acesso ao repositório. "
                f"URL: {url}. Mensagem: {message}"
            )

        if status == 404:
            raise GitHubApiError(
                f"Recurso não encontrado ao executar {operation}. "
                "Confira owner, repository, username e permissões do token. "
                f"URL: {url}. Mensagem: {message}"
            )

        if status == 422:
            raise GitHubApiError(
                f"O GitHub recusou os parâmetros ao executar {operation}. "
                "Verifique se branch, usuário e repositório existem. "
                f"URL: {url}. Mensagem: {message}"
            )

        if status == 429:
            reset_text = self._format_rate_reset(response.headers.get("X-RateLimit-Reset"))
            raise GitHubRateLimitError(
                f"Muitas requisições ao GitHub ao executar {operation}. "
                f"Tente novamente depois de {reset_text}."
            )

        if status >= 500:
            raise GitHubApiError(
                f"Erro interno do GitHub ao executar {operation}. "
                "Tente novamente mais tarde. "
                f"URL: {url}. Mensagem: {message}"
            )

        raise GitHubApiError(
            f"Erro na API do GitHub ao executar {operation}. "
            f"Status HTTP {status}. URL: {url}. Mensagem: {message}"
        )

    @staticmethod
    def _decode_json(response: requests.Response) -> Any:
        if not response.text:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubApiError(
                "A API do GitHub retornou uma resposta que não é JSON válido."
            ) from exc

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return (response.text or "").strip()[:500]

        if isinstance(payload, dict):
            return str(payload.get("message") or payload)[:500]
        return str(payload)[:500]

    @staticmethod
    def _format_rate_reset(reset_header: Optional[str]) -> str:
        if not reset_header:
            return "o horário indicado pelo GitHub"
        try:
            return datetime.fromtimestamp(int(reset_header)).isoformat(sep=" ", timespec="seconds")
        except ValueError:
            return "o horário indicado pelo GitHub"

    @staticmethod
    def _safe_url(response: requests.Response) -> str:
        return getattr(response, "url", "") or ""

    @staticmethod
    def _build_url(path_or_url: str) -> str:
        return path_or_url if path_or_url.startswith("http") else f"{API_BASE_URL}{path_or_url}"

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        time.sleep(min(2**attempt, 8))

    @staticmethod
    def _sleep_from_rate_headers(response: requests.Response, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            time.sleep(min(int(retry_after), 30))
            return
        time.sleep(min(2**attempt, 8))
