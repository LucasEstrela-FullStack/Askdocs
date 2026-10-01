"""Limpeza de texto que vem de fora (PDFs e respostas do modelo)."""

import re

# Caracteres de controle, inclusive o ESC que abre as sequências ANSI, e os
# invisíveis: hífen opcional, espaços de largura zero, BOM e marcas de direção
# (bidi). Com eles, um PDF consegue mexer no terminal, disfarçar um nome de
# arquivo nas fontes ou quebrar uma palavra ao meio sem que ninguém veja.
# Ficam como escapes de propósito: escritos literalmente, sumiriam da tela.
_INVISIVEIS = re.compile(
    r"[\x00-\x08\x0b-\x1f\x7f-\x9f"
    r"\u00ad\u200b\u200c\u200e\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]"
)


def sem_controle(texto: str) -> str:
    """Remove caracteres de controle e invisíveis, mantendo quebras de linha e tabulações."""
    return _INVISIVEIS.sub("", texto)
