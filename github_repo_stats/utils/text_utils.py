"""Funções para limpeza de texto exportável."""

from __future__ import annotations

from typing import Any


def clean_text(value: Any) -> str:
    """Remove quebras de linha e espaços externos de textos vindos da API."""

    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").strip()
