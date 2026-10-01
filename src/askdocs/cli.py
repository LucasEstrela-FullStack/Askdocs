"""Comandos de terminal: ``askdocs indexar`` e ``askdocs perguntar``.

Chroma, LangChain e o cliente do Ollama levam uns 6 s para importar, então eles
só são importados dentro dos comandos. Assim ``--help`` e erros de configuração
aparecem na hora.
"""

import argparse
import logging
import sys
import time
from typing import TYPE_CHECKING

from pydantic import ValidationError

from askdocs.config import Config
from askdocs.erros import ErroAskDocs
from askdocs.texto import sem_controle

if TYPE_CHECKING:
    from langchain_chroma import Chroma
    from langchain_ollama import ChatOllama

SAIR = {"", "sair", "exit", "quit"}


def cmd_indexar(cfg: Config) -> None:
    from askdocs.banco import indexar
    from askdocs.ingestao import carregar_documentos, dividir_em_chunks
    from askdocs.modelos import verificar_ollama

    verificar_ollama(cfg, cfg.modelo_embedding)
    inicio = time.perf_counter()

    paginas = carregar_documentos(cfg.pasta_base)
    chunks = dividir_em_chunks(paginas, cfg.tamanho_chunk, cfg.sobreposicao_chunk)
    print(f"{len(paginas)} páginas divididas em {len(chunks)} chunks.")

    resumo = indexar(
        chunks, cfg, lambda feitos, total: print(f"\rEmbeddings: {feitos}/{total}", end="", flush=True),
    )
    if resumo.novos:
        print()
    print(
        f"Base pronta em {cfg.pasta_db}: {resumo.total} chunks, {resumo.novos} novos e "
        f"{resumo.removidos} removidos ({time.perf_counter() - inicio:.0f}s)."
    )


def responder(pergunta: str, banco: "Chroma", llm: "ChatOllama", cfg: Config) -> None:
    from askdocs.consulta import buscar
    from askdocs.prompt import SEM_RESPOSTA, montar_mensagens

    trechos = buscar(pergunta, banco, cfg)
    if not trechos:
        print(SEM_RESPOSTA)
        return

    for parte in llm.stream(montar_mensagens(pergunta, trechos)):
        print(sem_controle(parte.content), end="", flush=True)
    print()

    paginas_por_fonte: dict[str, set[int]] = {}
    for doc in trechos:
        paginas_por_fonte.setdefault(doc.metadata["fonte"], set()).add(doc.metadata["pagina"])
    print("\nFontes:")
    for fonte, paginas in paginas_por_fonte.items():
        print(f"  - {fonte} (p. {', '.join(map(str, sorted(paginas)))})")


def cmd_perguntar(cfg: Config, pergunta: str | None) -> None:
    from askdocs.banco import abrir_banco, modelo_da_base, total_de_chunks
    from askdocs.modelos import criar_llm, verificar_ollama

    verificar_ollama(cfg, cfg.modelo_embedding, cfg.modelo_chat)
    if total_de_chunks(cfg) == 0:
        raise ErroAskDocs("A base está vazia. Rode primeiro: askdocs indexar")
    if (modelo := modelo_da_base(cfg)) != cfg.modelo_embedding:
        raise ErroAskDocs(
            f"A base foi indexada com outro modelo de embedding ({modelo or 'desconhecido'}). "
            "Rode: askdocs indexar"
        )

    banco, llm = abrir_banco(cfg), criar_llm(cfg)
    if pergunta:
        responder(pergunta, banco, llm, cfg)
        return

    print("AskDocs pronto. Pergunte sobre os seus documentos (Enter vazio ou 'sair' encerra).")
    while True:
        try:
            pergunta = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if pergunta.lower() in SAIR:
            return
        responder(pergunta, banco, llm, cfg)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askdocs", description="Perguntas e respostas sobre os seus PDFs, rodando só na sua máquina.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("indexar", help="lê os PDFs da pasta base e atualiza o banco vetorial")
    perguntar = sub.add_parser("perguntar", help="responde uma pergunta ou abre o modo conversa")
    perguntar.add_argument("pergunta", nargs="?", help="sem pergunta, abre o modo conversa")
    return parser


def _sair_com_erro(mensagem: str) -> None:
    print(f"erro: {mensagem}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="aviso: %(message)s")
    args = _parser().parse_args()

    try:
        cfg = Config()
    except ValidationError as erro:
        _sair_com_erro(f"configuração inválida no .env ou no ambiente:\n{erro}")

    import ollama

    from askdocs.modelos import execucao_local

    try:
        with execucao_local(cfg):
            if args.comando == "indexar":
                cmd_indexar(cfg)
            else:
                cmd_perguntar(cfg, args.pergunta)
    except ErroAskDocs as erro:
        _sair_com_erro(str(erro))
    except ollama.ResponseError as erro:
        _sair_com_erro(
            f"o Ollama falhou ao rodar o modelo: {erro.error}\n"
            "Se a GPU for antiga, tente ASKDOCS_OLLAMA_NUM_GPU=0 no .env."
        )
    except KeyboardInterrupt:
        sys.exit(130)
