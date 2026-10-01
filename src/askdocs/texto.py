"""Limpeza de texto que vem de fora (PDFs e respostas do modelo)."""

import re

# Caracteres de controle, inclusive o ESC que abre as sequências ANSI. Um PDF
# não pode usá-los para mexer no terminal de quem lê a resposta.
_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def sem_controle(texto: str) -> str:
    """Remove caracteres de controle, mantendo quebras de linha e tabulações."""
    return _CONTROLE.sub("", texto)
