import os
from pathlib import Path

import pytest
from langchain_core.documents import Document
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

from askdocs.config import Config


def criar_pdf(caminho: Path, paginas: list[str], senha: str | None = None) -> Path:
    """Cria um PDF com uma linha de texto por pagina (texto vazio = pagina em branco)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(caminho))
    for texto in paginas:
        if texto:
            canvas.drawString(72, 720, texto)
        canvas.showPage()
    canvas.save()

    if senha:
        escritor = PdfWriter()
        for pagina in PdfReader(caminho).pages:
            escritor.add_page(pagina)
        escritor.encrypt(senha)
        with caminho.open("wb") as arquivo:
            escritor.write(arquivo)
    return caminho


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config isolada: ignora o .env e as variaveis ASKDOCS_ da maquina."""
    for nome in [n for n in os.environ if n.startswith("ASKDOCS_")]:
        monkeypatch.delenv(nome)
    return Config(_env_file=None, pasta_base=tmp_path / "base", pasta_db=tmp_path / "db")


def doc(texto: str, fonte: str = "a.pdf", pagina: int = 1, **extra) -> Document:
    return Document(page_content=texto, metadata={"fonte": fonte, "pagina": pagina, **extra})
