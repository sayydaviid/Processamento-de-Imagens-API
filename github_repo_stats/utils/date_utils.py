"""Funções utilitárias para datas da API do GitHub."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    """Converte uma data ISO do GitHub para ``datetime``.

    O GitHub retorna datas em UTC com sufixo ``Z``. Valores vazios ou inválidos
    retornam ``None`` para evitar falhas ao consolidar dados incompletos.
    """

    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def unix_timestamp_to_date(value: int | float | None) -> str:
    """Converte timestamp Unix para data ISO, retornando vazio se inválido."""

    if value is None:
        return ""
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError, TypeError):
        return ""
