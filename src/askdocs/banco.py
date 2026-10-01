"""Banco vetorial: embeddings do Ollama persistidos no Chroma."""

import hashlib
from collections.abc import Callable

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from askdocs.config import Config

# Trechos por chamada ao Ollama: pequeno o bastante para mostrar progresso na CPU.
LOTE_EMBEDDING = 32


def abrir_banco(cfg: Config) -> Chroma:
    """Abre (ou cria) a colecao persistida em ``cfg.pasta_db``.

    A distancia e cosseno, para que a relevancia fique entre 0 e 1 e o limiar
    da configuracao tenha significado. A telemetria do Chroma fica desligada:
    nada do AskDocs sai da maquina.
    """
    return Chroma(
        collection_name=cfg.colecao,
        embedding_function=OllamaEmbeddings(
            model=cfg.modelo_embedding, base_url=cfg.ollama_url, num_gpu=cfg.ollama_num_gpu,
        ),
        persist_directory=str(cfg.pasta_db),
        collection_configuration={"hnsw": {"space": "cosine"}},
        client_settings=Settings(anonymized_telemetry=False),
    )


def total_de_chunks(banco: Chroma) -> int:
    return banco._collection.count()


def id_do_chunk(chunk: Document) -> str:
    """ID estavel derivado da origem do trecho: o mesmo PDF gera os mesmos IDs."""
    m = chunk.metadata
    origem = f"{m['fonte']}|{m['pagina']}|{m['start_index']}"
    return hashlib.sha1(origem.encode()).hexdigest()


def indexar(
    chunks: list[Document], cfg: Config, progresso: Callable[[int, int], None] | None = None,
) -> int:
    """Recria a colecao do zero com os chunks e devolve quantos foram gravados.

    Recriar (em vez de acrescentar) garante que PDFs removidos da pasta base
    tambem saiam do banco. Os embeddings sao gerados antes de apagar a colecao
    antiga: se o Ollama falhar no meio, a base anterior continua intacta.
    """
    banco = abrir_banco(cfg)
    textos = [c.page_content for c in chunks]

    vetores: list[list[float]] = []
    for inicio in range(0, len(textos), LOTE_EMBEDDING):
        vetores += banco.embeddings.embed_documents(textos[inicio:inicio + LOTE_EMBEDDING])
        if progresso:
            progresso(len(vetores), len(textos))

    banco.reset_collection()
    colecao = banco._collection
    lote = banco._client.get_max_batch_size()
    for inicio in range(0, len(chunks), lote):
        parte = chunks[inicio:inicio + lote]
        colecao.upsert(
            ids=[id_do_chunk(c) for c in parte],
            embeddings=vetores[inicio:inicio + lote],
            documents=[c.page_content for c in parte],
            metadatas=[c.metadata for c in parte],
        )
    return len(chunks)
