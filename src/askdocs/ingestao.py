"""Ingestao: transforma os PDFs da pasta base em documentos do LangChain."""

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from askdocs.erros import ErroAskDocs

log = logging.getLogger(__name__)


def carregar_documentos(pasta: Path) -> list[Document]:
    """Le cada pagina de cada PDF (inclusive em subpastas) como um Document.

    Os metadados guardam o arquivo, relativo a pasta, e a pagina comecando em 1,
    usados depois para citar a fonte da resposta.
    """
    if not pasta.is_dir():
        raise ErroAskDocs(f"Pasta de documentos nao encontrada: {pasta}")

    arquivos = sorted(pasta.rglob("*.pdf", case_sensitive=False))
    if not arquivos:
        raise ErroAskDocs(f"Nenhum PDF encontrado em {pasta}")

    documentos = []
    for arquivo in arquivos:
        fonte = arquivo.relative_to(pasta).as_posix()
        try:
            paginas = _ler_paginas(arquivo, fonte)
        except (PyPdfError, OSError) as erro:
            # O pypdf le sob demanda: senha e corrupcao podem aparecer em qualquer pagina.
            log.warning("Ignorando %s: nao foi possivel ler o PDF (%s)", fonte, erro)
            continue

        if not paginas:
            log.warning("%s nao tem texto extraivel (PDF escaneado precisa de OCR)", fonte)
        documentos.extend(paginas)

    if not documentos:
        raise ErroAskDocs(f"Nenhum PDF com texto extraivel em {pasta}")
    return documentos


def _ler_paginas(arquivo: Path, fonte: str) -> list[Document]:
    documentos = []
    for numero, pagina in enumerate(PdfReader(arquivo).pages, start=1):
        texto = (pagina.extract_text() or "").strip()
        if texto:
            documentos.append(
                Document(page_content=texto, metadata={"fonte": fonte, "pagina": numero})
            )
    return documentos


def dividir_em_chunks(documentos: list[Document], tamanho: int, sobreposicao: int) -> list[Document]:
    """Quebra as paginas em trechos menores, preferindo cortar em paragrafos e frases.

    A sobreposicao repete o fim de um trecho no inicio do proximo, para que uma
    regra cortada ao meio continue inteira em pelo menos um deles. O inicio de
    cada trecho na pagina fica em ``start_index``.
    """
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamanho, chunk_overlap=sobreposicao, add_start_index=True,
    )
    return divisor.split_documents(documentos)
