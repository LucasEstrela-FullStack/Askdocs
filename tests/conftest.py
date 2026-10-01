import os
from pathlib import Path

import pytest
from langchain_core.documents import Document
from pypdf import PdfWriter
from reportlab.pdfgen.canvas import Canvas

from askdocs.config import Config


def criar_pdf(caminho: Path, paginas: list[str], senha: str | None = None) -> None:
    """Cria um PDF com um texto por página ("\\n" quebra linha; vazio = página em branco)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(caminho))
    for texto in paginas:
        for i, linha in enumerate(texto.splitlines()):
            canvas.drawString(72, 720 - 16 * i, linha)
        canvas.showPage()
    canvas.save()

    if senha:
        escritor = PdfWriter(clone_from=caminho)
        escritor.encrypt(senha)
        escritor.write(caminho)


def doc(texto: str, fonte: str = "a.pdf", pagina: int = 1, **extra) -> Document:
    return Document(page_content=texto, metadata={"fonte": fonte, "pagina": pagina, **extra})


@pytest.fixture
def env_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tira do caminho as variáveis ASKDOCS_ desta máquina."""
    for nome in [n for n in os.environ if n.startswith("ASKDOCS_")]:
        monkeypatch.delenv(nome)


@pytest.fixture
def cfg(env_limpo, tmp_path: Path) -> Config:
    """Config com os padrões, sem ler o .env, e pastas temporárias."""
    return Config(_env_file=None, pasta_base=tmp_path / "base", pasta_db=tmp_path / "db")
