"""Exportador do resumo Markdown."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from github_repo_stats.exceptions import ExportError
from github_repo_stats.utils.text_utils import clean_text


class MarkdownExporter:
    """Gera o arquivo ``summary.md`` com o resumo da análise."""

    def save_summary(
        self,
        out_dir: Path,
        owner: str,
        repo: str,
        username: str,
        repo_data: dict[str, Any],
        user_stats: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        """Grava o resumo em Markdown."""

        path = out_dir / "summary.md"
        if path.exists() and not overwrite:
            raise ExportError(f"O resumo Markdown já existe e não será sobrescrito: {path}")

        try:
            path.write_text(
                self._build_summary(owner, repo, username, repo_data, user_stats),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ExportError(f"Não foi possível gravar o resumo Markdown {path}: {exc}") from exc

    def _build_summary(
        self,
        owner: str,
        repo: str,
        username: str,
        repo_data: dict[str, Any],
        user_stats: dict[str, Any],
    ) -> str:
        repo_url = f"https://github.com/{owner}/{repo}"
        contributors_url = f"{repo_url}/graphs/contributors"
        pulse_url = f"{repo_url}/pulse"
        code_frequency_url = f"{repo_url}/graphs/code-frequency"
        commits_url = f"{repo_url}/commits"
        profile_url = f"https://github.com/{username}"
        top_files_table = self._top_files_table(user_stats)

        return f"""# Estatísticas do repositório

## Identificação

- Repositório: `{owner}/{repo}`
- URL: {repo_url}
- Usuário analisado: `{username}`
- Perfil do usuário: {profile_url}
- Data de geração: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

## Dados gerais do repositório

- Nome: {repo_data.get("name", "")}
- Descrição: {clean_text(repo_data.get("description"))}
- Branch padrão: `{repo_data.get("default_branch", "")}`
- Privado: {repo_data.get("private", "")}
- Stars: {repo_data.get("stargazers_count", 0)}
- Forks: {repo_data.get("forks_count", 0)}
- Watchers: {repo_data.get("watchers_count", 0)}
- Issues abertas: {repo_data.get("open_issues_count", 0)}
- Criado em: {repo_data.get("created_at", "")}
- Atualizado em: {repo_data.get("updated_at", "")}
- Último push: {repo_data.get("pushed_at", "")}

## Estatísticas do usuário `{username}`

- Total de commits encontrados: **{user_stats.get("total_commits", 0)}**
- Total de linhas adicionadas: **{user_stats.get("total_additions", 0)}**
- Total de linhas removidas: **{user_stats.get("total_deletions", 0)}**
- Total de mudanças: **{user_stats.get("total_changes", 0)}**
- Eventos de alteração em arquivos: **{user_stats.get("total_file_change_events", 0)}**
- Arquivos únicos alterados: **{user_stats.get("total_unique_files_changed", 0)}**
- Primeiro commit encontrado: **{user_stats.get("first_commit_date", "")}**
- Último commit encontrado: **{user_stats.get("last_commit_date", "")}**
- Pull requests criados: **{user_stats.get("total_pull_requests_authored", 0)}**
- Issues criadas: **{user_stats.get("total_issues_authored", 0)}**
- Comentários em issues: **{user_stats.get("total_issue_comments_authored", 0)}**
- Comentários de revisão em PRs: **{user_stats.get("total_pr_review_comments_authored", 0)}**

## Arquivos mais alterados

| Arquivo | Commits | Adições | Remoções | Alterações |
|---|---:|---:|---:|---:|
{top_files_table}

## Links para prints do relatório

Use estes links para tirar prints e colocar no relatório:

- Gráfico de contribuidores: {contributors_url}
- Pulse do repositório: {pulse_url}
- Frequência de código: {code_frequency_url}
- Histórico de commits do repositório: {commits_url}
- Perfil do usuário para print do gráfico verde de contribuições: {profile_url}

## Arquivos gerados

A pasta gerada contém:

- `summary.json`: resumo geral consolidado.
- `summary.md`: este resumo em Markdown.
- `csv/my_commits.csv`: commits do usuário.
- `csv/my_commit_files.csv`: arquivos alterados por commit.
- `csv/my_commits_by_day.csv`: commits por dia.
- `csv/my_commits_by_week.csv`: commits por semana.
- `csv/my_file_churn.csv`: arquivos mais alterados.
- `csv/contributors.csv`: contribuidores do repositório.
- `csv/languages.csv`: linguagens do repositório.
- `csv/my_pull_requests.csv`: PRs criados pelo usuário.
- `csv/my_issues.csv`: issues criadas pelo usuário.
- `csv/my_issue_comments.csv`: comentários em issues.
- `csv/my_pr_review_comments.csv`: comentários em PRs.
- `csv/repo_stats_*.csv`: estatísticas oficiais do GitHub Insights.
- `charts/*.png`: gráficos prontos para usar no relatório.
"""

    @staticmethod
    def _top_files_table(user_stats: dict[str, Any]) -> str:
        lines: list[str] = []
        for item in user_stats.get("top_files_by_changes", [])[:15]:
            lines.append(
                f"| `{item['filename']}` | {item['commits']} | {item['additions']} | "
                f"{item['deletions']} | {item['changes']} |"
            )
        return "\n".join(lines)
