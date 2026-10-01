"""Erros esperados do AskDocs, mostrados ao usuario sem traceback."""


class ErroAskDocs(Exception):
    """Falha que o usuario consegue corrigir (pasta vazia, Ollama parado...)."""
