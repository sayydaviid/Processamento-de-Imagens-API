"""Configuração centralizada de logs."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura logs no terminal e retorna o logger principal."""

    logger = logging.getLogger()
    logger.setLevel(level)

    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(stream_handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    return logging.getLogger("github_repo_stats")


def add_file_handler(log_file: Path, level: int = logging.INFO) -> None:
    """Adiciona gravação de logs em arquivo dentro da pasta de saída."""

    root_logger = logging.getLogger()
    if any(isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file) for handler in root_logger.handlers):
        return

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)
