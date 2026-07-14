"""Exceções usadas para falhas controladas da aplicação."""


class GitHubApiError(Exception):
    """Erro genérico ao consultar ou interpretar a API do GitHub."""


class GitHubAuthenticationError(GitHubApiError):
    """Erro de autenticação ou token inválido."""


class GitHubRateLimitError(GitHubApiError):
    """Erro causado por limite de requisições da API do GitHub."""


class ConfigurationError(Exception):
    """Erro de configuração da aplicação."""


class ExportError(Exception):
    """Erro ao gravar arquivos de saída."""
