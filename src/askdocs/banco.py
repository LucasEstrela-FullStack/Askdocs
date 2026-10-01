"""Banco vetorial: embeddings do Ollama persistidos no Chroma."""

import hashlib

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from askdocs.config import Config


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


def id_do_chunk(chunk: Document) -> str:
    """ID estavel derivado da origem do trecho: o mesmo PDF gera os mesmos IDs."""
    m = chunk.metadata
    origem = f"{m['fonte']}|{m['pagina']}|{m['start_index']}"
    return hashlib.sha1(origem.encode()).hexdigest()


def indexar(chunks: list[Document], cfg: Config) -> int:
    """Recria a colecao do zero com os chunks e devolve quantos foram gravados.

    Recriar (em vez de acrescentar) garante que PDFs removidos da pasta base
    tambem saiam do banco.
    """
    banco = abrir_banco(cfg)
    banco.reset_collection()
    if chunks:
        banco.add_documents(chunks, ids=[id_do_chunk(c) for c in chunks])
    return len(chunks)
