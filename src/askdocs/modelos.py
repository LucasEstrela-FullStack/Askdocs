"""Tudo que fala com o Ollama: criação dos modelos, checagem e execução local."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import ollama
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langsmith import tracing_context

from askdocs.config import Config
from askdocs.erros import ErroAskDocs

log = logging.getLogger(__name__)


def criar_embeddings(cfg: Config) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=cfg.modelo_embedding, base_url=cfg.ollama_url,
        num_gpu=cfg.ollama_num_gpu, keep_alive=cfg.ollama_keep_alive,
    )


def criar_llm(cfg: Config) -> ChatOllama:
    return ChatOllama(
        model=cfg.modelo_chat, base_url=cfg.ollama_url, temperature=cfg.temperatura,
        num_gpu=cfg.ollama_num_gpu, keep_alive=cfg.ollama_keep_alive,
    )


def verificar_ollama(cfg: Config, *modelos: str) -> None:
    """Falha logo no início, dizendo o que fazer, se faltar o Ollama ou um modelo."""
    try:
        instalados = {m.model for m in ollama.Client(host=cfg.ollama_url).list().models}
    except ConnectionError as erro:
        raise ErroAskDocs(f"O Ollama não respondeu em {cfg.ollama_url}. Ele está aberto?") from erro

    for modelo in modelos:
        nome = modelo if ":" in modelo else f"{modelo}:latest"
        if nome not in instalados:
            raise ErroAskDocs(f"O modelo '{modelo}' não está instalado. Rode: ollama pull {modelo}")


@contextmanager
def execucao_local(cfg: Config) -> Iterator[None]:
    """Mantém perguntas e trechos dos PDFs dentro desta máquina enquanto o bloco roda.

    Desliga o envio de rastros ao LangSmith mesmo que LANGSMITH_TRACING esteja
    ligada no ambiente, e avisa quando o Ollama configurado é de outra máquina.
    """
    if not cfg.ollama_e_local:
        log.warning("Ollama em %s: perguntas e trechos dos PDFs vão sair desta máquina", cfg.ollama_url)
    with tracing_context(enabled=False):
        yield
