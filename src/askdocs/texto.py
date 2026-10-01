"""Limpeza de texto que vem de fora (PDFs e respostas do modelo)."""

import re

# Caracteres de controle, inclusive o ESC que abre as sequências ANSI, e os
# invisíveis: hífen opcional, espaços de largura zero, BOM e marcas de direção
# (bidi). Com eles, um PDF consegue mexer no terminal, disfarçar um nome de
# arquivo nas fontes ou quebrar uma palavra ao meio sem que ninguém veja.
_INVISIVEIS = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f"
    "­​‌‎‏‪-‮⁠-⁤⁦-⁩﻿]"
)


def sem_controle(texto: str) -> str:
    """Remove caracteres de controle e invisíveis, mantendo quebras de linha e tabulações."""
    return _INVISIVEIS.sub("", texto)
