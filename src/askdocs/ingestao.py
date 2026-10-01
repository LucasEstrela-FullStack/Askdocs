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

    arquivos = sorted(pasta.rglob("*.pdf"))
    if not arquivos:
        raise ErroAskDocs(f"Nenhum PDF encontrado em {pasta}")

    documentos = []
    for arquivo in arquivos:
        fonte = arquivo.relative_to(pasta).as_posix()
        try:
            paginas = PdfReader(arquivo).pages
        except (PyPdfError, OSError) as erro:
            log.warning("Ignorando %s: nao foi possivel ler o PDF (%s)", fonte, erro)
            continue

        antes = len(documentos)
        for numero, pagina in enumerate(paginas, start=1):
            texto = (pagina.extract_text() or "").strip()
            if texto:
                documentos.append(
                    Document(page_content=texto, metadata={"fonte": fonte, "pagina": numero})
                )

        if len(documentos) == antes:
            log.warning("%s nao tem texto extraivel (PDF escaneado precisa de OCR)", fonte)

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
