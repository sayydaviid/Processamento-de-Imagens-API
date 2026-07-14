"""Funções para criação de pastas e nomes de arquivos."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def ensure_output_dir(base_name: str, root: Path | str = ".") -> Path:
    """Cria a pasta de saída com subpastas ``csv``, ``json`` e ``charts``.

    A estrutura preserva o padrão anterior: ``github_stats_<repo>_<user>_<timestamp>``.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_base_name = sanitize_path_part(base_name)
    output_dir = Path(root) / f"{safe_base_name}_{timestamp}"
    counter = 1
    while output_dir.exists():
        output_dir = Path(root) / f"{safe_base_name}_{timestamp}_{counter}"
        counter += 1

    output_dir.mkdir(parents=True)
    (output_dir / "csv").mkdir(exist_ok=True)
    (output_dir / "json").mkdir(exist_ok=True)
    (output_dir / "charts").mkdir(exist_ok=True)
    return output_dir


def sanitize_path_part(value: str) -> str:
    """Remove caracteres incompatíveis com nomes de pasta em sistemas comuns."""

    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in value)
    return cleaned.strip() or "github_stats"
