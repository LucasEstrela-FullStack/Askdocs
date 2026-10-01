"""Ingestao: transforma os PDFs da pasta base em documentos do LangChain."""

import logging
from pathlib import Path

from langchain_core.documents import Document
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
