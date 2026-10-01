import logging

import pytest
from conftest import criar_pdf, doc

from askdocs.erros import ErroAskDocs
from askdocs.ingestao import carregar_documentos, dividir_em_chunks


def test_carrega_uma_entrada_por_pagina_com_fonte_e_pagina(tmp_path):
    criar_pdf(tmp_path / "manual.pdf", ["Primeira pagina", "Segunda pagina"])
    criar_pdf(tmp_path / "sub" / "anexo.pdf", ["Anexo"])

    docs = carregar_documentos(tmp_path)

    assert [(d.metadata["fonte"], d.metadata["pagina"]) for d in docs] == [
        ("manual.pdf", 1), ("manual.pdf", 2), ("sub/anexo.pdf", 1),
    ]
    assert docs[1].page_content == "Segunda pagina"


def test_pula_paginas_em_branco_mantendo_a_numeracao(tmp_path):
    criar_pdf(tmp_path / "a.pdf", ["Capa", "", "Conteudo"])
    assert [d.metadata["pagina"] for d in carregar_documentos(tmp_path)] == [1, 3]


def test_aceita_extensao_maiuscula(tmp_path):
    criar_pdf(tmp_path / "RELATORIO.PDF", ["Texto"])
    assert len(carregar_documentos(tmp_path)) == 1


def test_pula_pdf_protegido_por_senha_e_avisa(tmp_path, caplog):
    criar_pdf(tmp_path / "secreto.pdf", ["Sigiloso"], senha="123")
    criar_pdf(tmp_path / "aberto.pdf", ["Publico"])

    with caplog.at_level(logging.WARNING):
        docs = carregar_documentos(tmp_path)

    assert [d.metadata["fonte"] for d in docs] == ["aberto.pdf"]
    assert "secreto.pdf" in caplog.text


def test_pula_arquivo_que_nao_e_pdf_de_verdade(tmp_path):
    (tmp_path / "quebrado.pdf").write_text("nao sou um pdf")
    criar_pdf(tmp_path / "bom.pdf", ["Ok"])
    assert [d.metadata["fonte"] for d in carregar_documentos(tmp_path)] == ["bom.pdf"]


def test_erro_quando_a_pasta_nao_existe(tmp_path):
    with pytest.raises(ErroAskDocs, match="nao encontrada"):
        carregar_documentos(tmp_path / "nada")


def test_erro_quando_nao_ha_pdf(tmp_path):
    (tmp_path / "notas.txt").write_text("oi")
    with pytest.raises(ErroAskDocs, match="Nenhum PDF encontrado"):
        carregar_documentos(tmp_path)


def test_erro_quando_nenhum_pdf_tem_texto(tmp_path):
    criar_pdf(tmp_path / "escaneado.pdf", ["", ""])
    with pytest.raises(ErroAskDocs, match="texto extraivel"):
        carregar_documentos(tmp_path)


def test_chunks_respeitam_tamanho_e_guardam_origem():
    texto = " ".join(f"frase{i}." for i in range(400))
    chunks = dividir_em_chunks([doc(texto, pagina=7)], tamanho=200, sobreposicao=50)

    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)
    assert all(c.metadata["pagina"] == 7 for c in chunks)
    assert [c.metadata["start_index"] for c in chunks] == sorted(c.metadata["start_index"] for c in chunks)


def test_chunks_consecutivos_se_sobrepoem():
    texto = " ".join(f"palavra{i}" for i in range(300))
    primeiro, segundo, *_ = dividir_em_chunks([doc(texto)], tamanho=200, sobreposicao=60)
    assert primeiro.page_content.split()[-1] in segundo.page_content
