"""Ingestão: transforma os PDFs da pasta base em documentos do LangChain."""

import logging
import re
from collections import Counter
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from askdocs.erros import ErroAskDocs
from askdocs.texto import sem_controle

log = logging.getLogger(__name__)

# Com menos páginas, uma linha repetida pode ser conteúdo, não cabeçalho.
MIN_PAGINAS_CABECALHO = 3
LINHAS_DA_BORDA = 4

_NUMEROS = re.compile(r"\d+")
# Pontilhado de sumário ("Férias . . . . . 3"): só ruído para a busca.
_PONTILHADO = re.compile(r"(?:[ \t]*\.){4,}[ \t]*")


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
        except Exception as erro:
            # O pypdf lê sob demanda, então senha ou arquivo corrompido podem
            # estourar em qualquer página. Em PDF malformado ele também solta
            # KeyError, ValueError e afins, não só PyPdfError. Um arquivo ruim
            # não pode derrubar a indexação dos outros.
            log.warning("Ignorando %s: não foi possível ler o PDF (%s)", fonte, sem_controle(str(erro)))
            continue

        if not paginas:
            log.warning("%s não tem texto para extrair (PDF escaneado precisa de OCR)", fonte)
        documentos.extend(paginas)

    if not documentos:
        raise ErroAskDocs(f"Nenhum PDF com texto para extrair em {pasta}")
    return documentos


def _ler_paginas(arquivo: Path, fonte: str) -> list[Document]:
    textos = [sem_controle(pagina.extract_text() or "") for pagina in PdfReader(arquivo).pages]
    repetidas = _linhas_repetidas(textos)

    documentos = []
    for numero, texto in enumerate(textos, start=1):
        texto = _limpar_pagina(texto, repetidas)
        if texto:
            documentos.append(
                Document(page_content=texto, metadata={"fonte": fonte, "pagina": numero})
            )
    return documentos


def _chave_da_linha(linha: str) -> str:
    # "Página 3" e "Página 4" são a mesma linha de rodapé.
    return _NUMEROS.sub("#", linha.strip())


def _indices_da_borda(linhas: list[str]) -> set[int]:
    """Posições das primeiras e últimas linhas com texto, onde ficam cabeçalho e rodapé."""
    com_texto = [i for i, linha in enumerate(linhas) if linha.strip()]
    return set(com_texto[:LINHAS_DA_BORDA] + com_texto[-LINHAS_DA_BORDA:])


def _linhas_repetidas(textos: list[str]) -> set[str]:
    """Linhas da borda presentes em mais da metade das páginas: cabeçalho e rodapé.

    Elas não dizem nada sobre o conteúdo e, como entram em todo trecho, deixam
    os embeddings de páginas diferentes parecidos entre si. Só a borda conta,
    para que um conteúdo que muda só nos números ("Item 1", "Item 2") não pareça
    rodapé.
    """
    if len(textos) < MIN_PAGINAS_CABECALHO:
        return set()
    contagem = Counter()
    for texto in textos:
        linhas = texto.splitlines()
        contagem.update({_chave_da_linha(linhas[i]) for i in _indices_da_borda(linhas)})
    return {chave for chave, vezes in contagem.items() if vezes > len(textos) / 2}


def _limpar_pagina(texto: str, repetidas: set[str]) -> str:
    linhas = texto.splitlines()
    borda = _indices_da_borda(linhas)
    mantidas = (
        linha for i, linha in enumerate(linhas)
        if i not in borda or _chave_da_linha(linha) not in repetidas
    )
    return _PONTILHADO.sub(" ", "\n".join(mantidas)).strip()


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
