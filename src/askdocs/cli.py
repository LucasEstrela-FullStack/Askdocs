"""Interface de terminal: ``askdocs indexar`` e ``askdocs perguntar``."""

import argparse
import logging
import os
import re
import sys
import time
from urllib.parse import urlparse

import ollama
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from askdocs.banco import abrir_banco, indexar, total_de_chunks
from askdocs.config import Config, carregar_config
from askdocs.consulta import buscar
from askdocs.erros import ErroAskDocs
from askdocs.ingestao import carregar_documentos, dividir_em_chunks
from askdocs.prompt import SEM_RESPOSTA, montar_mensagens

SAIR = {"", "sair", "exit", "quit"}

# Caracteres de controle (inclusive ESC, que inicia sequencias ANSI). Texto vindo
# do PDF, ou repetido pelo modelo, nao pode mexer no terminal de quem le.
_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

# Com qualquer uma ligada, o LangChain envia perguntas e trechos para o LangSmith.
_RASTREAMENTO = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING")

_HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1"}

log = logging.getLogger(__name__)


def seguro(texto: str) -> str:
    return _CONTROLE.sub("", texto)


def garantir_execucao_local(cfg: Config) -> None:
    """Desliga o envio de rastros ao LangSmith e avisa se o Ollama for remoto."""
    for variavel in _RASTREAMENTO:
        if os.environ.get(variavel, "").lower() == "true":
            os.environ[variavel] = "false"
            log.warning("%s desligada: o AskDocs nao envia dados para o LangSmith", variavel)

    host = urlparse(cfg.ollama_url).hostname
    if host not in _HOSTS_LOCAIS:
        log.warning("Ollama em %s: perguntas e trechos dos PDFs vao sair desta maquina", host)


def criar_llm(cfg: Config) -> ChatOllama:
    return ChatOllama(
        model=cfg.modelo_chat, base_url=cfg.ollama_url,
        temperature=cfg.temperatura, num_gpu=cfg.ollama_num_gpu,
    )


def verificar_ollama(cfg: Config, *modelos: str) -> None:
    """Falha cedo, com instrucao clara, se o Ollama ou algum modelo nao estiver disponivel."""
    try:
        instalados = {m.model for m in ollama.Client(host=cfg.ollama_url).list().models}
    except ConnectionError as erro:
        raise ErroAskDocs(f"Ollama nao respondeu em {cfg.ollama_url}. Ele esta aberto?") from erro

    for modelo in modelos:
        nome = modelo if ":" in modelo else f"{modelo}:latest"
        if nome not in instalados:
            raise ErroAskDocs(f"Modelo '{modelo}' nao instalado. Rode: ollama pull {modelo}")


def cmd_indexar(cfg: Config) -> None:
    verificar_ollama(cfg, cfg.modelo_embedding)
    inicio = time.perf_counter()

    paginas = carregar_documentos(cfg.pasta_base)
    chunks = dividir_em_chunks(paginas, cfg.tamanho_chunk, cfg.sobreposicao_chunk)
    print(f"{len(paginas)} paginas divididas em {len(chunks)} chunks.")
    indexar(chunks, cfg, lambda feitos, total: print(f"\rEmbeddings: {feitos}/{total}", end="", flush=True))
    print()

    print(f"Base pronta em {cfg.pasta_db} ({time.perf_counter() - inicio:.0f}s).")


def responder(pergunta: str, banco: Chroma, llm: ChatOllama, cfg: Config) -> None:
    trechos = buscar(pergunta, banco, cfg)
    if not trechos:
        print(SEM_RESPOSTA)
        return

    for parte in llm.stream(montar_mensagens(pergunta, [doc for doc, _ in trechos])):
        print(seguro(parte.content), end="", flush=True)
    print()

    paginas_por_fonte: dict[str, set[int]] = {}
    for doc, _ in trechos:
        paginas_por_fonte.setdefault(doc.metadata["fonte"], set()).add(doc.metadata["pagina"])
    print("\nFontes:")
    for fonte, paginas in paginas_por_fonte.items():
        print(f"  - {seguro(fonte)} (p. {', '.join(map(str, sorted(paginas)))})")


def cmd_perguntar(cfg: Config, pergunta: str | None) -> None:
    verificar_ollama(cfg, cfg.modelo_embedding, cfg.modelo_chat)
    banco = abrir_banco(cfg)
    if total_de_chunks(banco) == 0:
        raise ErroAskDocs("A base esta vazia. Rode primeiro: askdocs indexar")

    llm = criar_llm(cfg)

    if pergunta:
        responder(pergunta, banco, llm, cfg)
        return

    print("AskDocs pronto. Pergunte sobre seus documentos (Enter vazio ou 'sair' encerra).")
    while True:
        try:
            pergunta = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if pergunta.lower() in SAIR:
            return
        responder(pergunta, banco, llm, cfg)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="aviso: %(message)s")

    parser = argparse.ArgumentParser(
        prog="askdocs", description="Perguntas e respostas sobre seus PDFs, 100% local.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("indexar", help="le os PDFs da pasta base e (re)cria o banco vetorial")
    p_perguntar = sub.add_parser("perguntar", help="responde uma pergunta ou abre o modo conversa")
    p_perguntar.add_argument("pergunta", nargs="?", help="sem pergunta, abre o modo conversa")
    args = parser.parse_args()

    try:
        cfg = carregar_config()
        garantir_execucao_local(cfg)
        if args.comando == "indexar":
            cmd_indexar(cfg)
        else:
            cmd_perguntar(cfg, args.pergunta)
    except ErroAskDocs as erro:
        print(f"erro: {erro}", file=sys.stderr)
        sys.exit(1)
    except ValidationError as erro:
        print(f"erro: configuracao invalida no .env ou no ambiente:\n{erro}", file=sys.stderr)
        sys.exit(1)
    except ollama.ResponseError as erro:
        print(
            f"erro: o Ollama falhou ao rodar o modelo: {erro.error}\n"
            "Se a GPU for antiga, tente ASKDOCS_OLLAMA_NUM_GPU=0 no .env.",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
