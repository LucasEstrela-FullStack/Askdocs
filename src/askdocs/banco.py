"""Banco vetorial: embeddings do Ollama guardados no Chroma."""

import hashlib
from collections.abc import Callable
from typing import NamedTuple

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from chromadb.utils.batch_utils import create_batches
from langchain_chroma import Chroma
from langchain_core.documents import Document

from askdocs.config import Config
from askdocs.modelos import criar_embeddings

# Trechos por chamada ao Ollama: pouco o bastante para mostrar progresso na CPU.
LOTE_EMBEDDING = 32

# Cosseno deixa a relevância entre 0 e 1, a mesma escala do limiar da config.
DISTANCIA = {"hnsw": {"space": "cosine"}}


class ResumoIndexacao(NamedTuple):
    novos: int
    removidos: int
    total: int


def _cliente(cfg: Config) -> ClientAPI:
    # Telemetria desligada: nada do AskDocs sai da máquina.
    return chromadb.PersistentClient(
        path=str(cfg.pasta_db), settings=Settings(anonymized_telemetry=False),
    )


def _colecao(cliente: ClientAPI, cfg: Config) -> Collection:
    return cliente.get_or_create_collection(cfg.colecao, configuration=DISTANCIA)


def abrir_banco(cfg: Config) -> Chroma:
    return Chroma(
        client=_cliente(cfg), collection_name=cfg.colecao,
        embedding_function=criar_embeddings(cfg), collection_configuration=DISTANCIA,
    )


def total_de_chunks(cfg: Config) -> int:
    return _colecao(_cliente(cfg), cfg).count()


def modelo_da_base(cfg: Config) -> str | None:
    """Modelo de embedding usado na última indexação (None se a base é antiga ou nova)."""
    return (_colecao(_cliente(cfg), cfg).metadata or {}).get("modelo_embedding")


def id_do_chunk(chunk: Document) -> str:
    """Muda junto com o trecho: é assim que a reindexação sabe o que mudou."""
    m = chunk.metadata
    chave = f"{m['fonte']}|{m['pagina']}|{m['start_index']}|{chunk.page_content}"
    return hashlib.sha1(chave.encode()).hexdigest()


def indexar(
    chunks: list[Document], cfg: Config, progresso: Callable[[int, int], None] | None = None,
) -> ResumoIndexacao:
    """Deixa a coleção igual a ``chunks``, gerando embedding só do que é novo.

    O que já está no banco com o mesmo ID fica como está, e o que sumiu (PDF
    removido ou editado) sai. Os embeddings são calculados antes de qualquer
    escrita, então uma falha do Ollama não estraga a base. Trocar o modelo de
    embedding refaz tudo: vetores de modelos diferentes não se comparam.
    """
    cliente = _cliente(cfg)
    colecao = _colecao(cliente, cfg)
    reconstruir = (colecao.metadata or {}).get("modelo_embedding") != cfg.modelo_embedding
    existentes = set() if reconstruir else set(colecao.get(include=[])["ids"])

    por_id = {id_do_chunk(c): c for c in chunks}
    pendentes = {i: c for i, c in por_id.items() if i not in existentes}
    textos = [c.page_content for c in pendentes.values()]
    vetores = _gerar_embeddings(textos, cfg, progresso)

    if reconstruir:
        cliente.delete_collection(cfg.colecao)
        colecao = cliente.create_collection(
            cfg.colecao, configuration=DISTANCIA,
            metadata={"modelo_embedding": cfg.modelo_embedding},
        )

    if pendentes:
        lotes = create_batches(
            cliente, ids=list(pendentes), embeddings=vetores, documents=textos,
            metadatas=[c.metadata for c in pendentes.values()],
        )
        for ids, embeddings, metadatas, documents in lotes:
            colecao.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    obsoletos = sorted(existentes - por_id.keys())
    lote = cliente.get_max_batch_size()
    for inicio in range(0, len(obsoletos), lote):
        colecao.delete(ids=obsoletos[inicio:inicio + lote])

    return ResumoIndexacao(novos=len(pendentes), removidos=len(obsoletos), total=len(por_id))


def _gerar_embeddings(
    textos: list[str], cfg: Config, progresso: Callable[[int, int], None] | None,
) -> list[list[float]]:
    modelo = criar_embeddings(cfg)
    vetores: list[list[float]] = []
    for inicio in range(0, len(textos), LOTE_EMBEDDING):
        vetores += modelo.embed_documents(textos[inicio:inicio + LOTE_EMBEDDING])
        if progresso:
            progresso(len(vetores), len(textos))
    return vetores
