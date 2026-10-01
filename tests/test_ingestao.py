import logging

import pytest
from conftest import criar_pdf, doc

from askdocs import ingestao
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


def test_falha_inesperada_do_pypdf_pula_so_aquele_arquivo(tmp_path, monkeypatch, caplog):
    criar_pdf(tmp_path / "estranho.pdf", ["X"])
    criar_pdf(tmp_path / "bom.pdf", ["Ok"])
    leitor_real = ingestao.PdfReader

    def leitor(caminho):
        if caminho.name == "estranho.pdf":
            raise KeyError("/Root")  # o que o pypdf solta em alguns PDFs malformados
        return leitor_real(caminho)

    monkeypatch.setattr(ingestao, "PdfReader", leitor)
    with caplog.at_level(logging.WARNING):
        docs = carregar_documentos(tmp_path)

    assert [d.metadata["fonte"] for d in docs] == ["bom.pdf"]
    assert "estranho.pdf" in caplog.text


TEMAS = ["ferias", "beneficios", "reembolso", "seguranca"]


def pagina(numero: int, *meio: str) -> str:
    tema = TEMAS[numero - 1]
    partes = ["Regras", "Prazo", "Limite", "Contato", "Excecoes", "Exemplos", "Duvidas", "Historico"]
    corpo = [f"{parte} de {tema}" for parte in partes]
    return "\n".join(["ACME LTDA", *corpo[:4], *meio, *corpo[4:], f"Pagina {numero}"])


def test_remove_cabecalho_e_rodape_repetidos(tmp_path):
    criar_pdf(tmp_path / "a.pdf", [pagina(n) for n in range(1, 5)])
    primeira = carregar_documentos(tmp_path)[0].page_content.splitlines()
    assert primeira[0] == "Regras de ferias"
    assert primeira[-1] == "Historico de ferias"
    assert len(primeira) == 8


def test_linha_repetida_no_meio_da_pagina_e_conteudo(tmp_path):
    criar_pdf(tmp_path / "a.pdf", [pagina(n, "Aviso importante", "Item 7") for n in range(1, 5)])
    primeira = carregar_documentos(tmp_path)[0].page_content
    assert "Aviso importante\nItem 7" in primeira
    assert "ACME LTDA" not in primeira


def test_linha_em_metade_das_paginas_ou_menos_fica(tmp_path):
    criar_pdf(tmp_path / "a.pdf", ["Aviso\nUm", "Aviso\nDois", "Tres", "Quatro"])
    assert carregar_documentos(tmp_path)[0].page_content == "Aviso\nUm"


def test_com_poucas_paginas_nada_e_tratado_como_cabecalho(tmp_path):
    criar_pdf(tmp_path / "a.pdf", ["ACME\nUm", "ACME\nDois"])
    assert [d.page_content for d in carregar_documentos(tmp_path)] == ["ACME\nUm", "ACME\nDois"]


def test_remove_pontilhado_de_sumario_e_mantem_reticencias(tmp_path):
    criar_pdf(tmp_path / "a.pdf", ["1. Ferias . . . . . . . 3\nE depois... nada"])
    assert carregar_documentos(tmp_path)[0].page_content == "1. Ferias 3\nE depois... nada"


def test_erro_quando_a_pasta_nao_existe(tmp_path):
    with pytest.raises(ErroAskDocs, match="não encontrada"):
        carregar_documentos(tmp_path / "nada")


def test_erro_quando_nao_ha_pdf(tmp_path):
    (tmp_path / "notas.txt").write_text("oi")
    with pytest.raises(ErroAskDocs, match="Nenhum PDF encontrado"):
        carregar_documentos(tmp_path)


def test_erro_quando_nenhum_pdf_tem_texto(tmp_path):
    criar_pdf(tmp_path / "escaneado.pdf", ["", ""])
    with pytest.raises(ErroAskDocs, match="texto para extrair"):
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
