"""Erros que o AskDocs mostra ao usuário sem traceback."""


class ErroAskDocs(Exception):
    """Problema que o próprio usuário resolve, como pasta vazia ou Ollama fechado."""
