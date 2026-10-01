"""Ingestão: transforma os PDFs da pasta base em documentos do LangChain."""

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from askdocs.erros import ErroAskDocs
from askdocs.texto import sem_controle

log = logging.getLogger(__name__)


def carregar_documentos(pasta: Path) -> list[Document]:
    """Lê cada página de cada PDF (subpastas incluídas) como um Document.

    Os metadados guardam o arquivo, relativo à pasta, e a página a partir de 1,
    para a resposta poder citar a fonte. Texto e nome do arquivo saem daqui sem
    caracteres de controle, então o banco, o prompt e o terminal recebem texto limpo.
    """
    if not pasta.is_dir():
        raise ErroAskDocs(f"Pasta de documentos não encontrada: {pasta}")

    arquivos = sorted(pasta.rglob("*.pdf", case_sensitive=False))
    if not arquivos:
        raise ErroAskDocs(f"Nenhum PDF encontrado em {pasta}")

    documentos = []
    for arquivo in arquivos:
        fonte = sem_controle(arquivo.relative_to(pasta).as_posix())
        try:
            paginas = _ler_paginas(arquivo, fonte)
        except (PyPdfError, OSError) as erro:
            # O pypdf lê sob demanda: senha ou arquivo corrompido podem aparecer em qualquer página.
            log.warning("Ignorando %s: não foi possível ler o PDF (%s)", fonte, sem_controle(str(erro)))
            continue

        if not paginas:
            log.warning("%s não tem texto para extrair (PDF escaneado precisa de OCR)", fonte)
        documentos.extend(paginas)

    if not documentos:
        raise ErroAskDocs(f"Nenhum PDF com texto para extrair em {pasta}")
    return documentos


def _ler_paginas(arquivo: Path, fonte: str) -> list[Document]:
    documentos = []
    for numero, pagina in enumerate(PdfReader(arquivo).pages, start=1):
        texto = sem_controle(pagina.extract_text() or "").strip()
        if texto:
            documentos.append(
                Document(page_content=texto, metadata={"fonte": fonte, "pagina": numero})
            )
    return documentos


def dividir_em_chunks(documentos: list[Document], tamanho: int, sobreposicao: int) -> list[Document]:
    """Quebra as páginas em trechos menores, cortando de preferência entre parágrafos e frases.

    A sobreposição repete o fim de um trecho no começo do próximo. Assim, uma
    regra cortada ao meio continua inteira em pelo menos um deles. A posição de
    cada trecho na página fica em ``start_index``.
    """
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamanho, chunk_overlap=sobreposicao, add_start_index=True,
    )
    return divisor.split_documents(documentos)
