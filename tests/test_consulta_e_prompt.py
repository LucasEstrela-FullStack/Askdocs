from conftest import doc

from askdocs.consulta import buscar
from askdocs.prompt import SEM_RESPOSTA, formatar_contexto, montar_mensagens
from askdocs.texto import sem_controle


class BancoFalso:
    def __init__(self, *resultados):
        self.resultados = list(resultados)

    def similarity_search_with_relevance_scores(self, pergunta, k):
        self.chamada = (pergunta, k)
        return self.resultados


def test_buscar_usa_k_e_corta_no_limiar_inclusive(cfg):
    banco = BancoFalso(
        (doc("alto"), 0.9), (doc("no limiar"), cfg.limiar_relevancia), (doc("baixo"), 0.1),
    )
    assert [d.page_content for d in buscar("pergunta?", banco, cfg)] == ["alto", "no limiar"]
    assert banco.chamada == ("pergunta?", cfg.k)


def test_contexto_numera_trechos_e_cita_a_fonte():
    contexto = formatar_contexto([doc("Texto A", "x.pdf", 2), doc("Texto B", "y.pdf", 9)])
    assert contexto.startswith("[1] x.pdf, página 2\nTexto A")
    assert "[2] y.pdf, página 9\nTexto B" in contexto


def test_mensagens_trazem_regras_contexto_e_pergunta():
    sistema, humano = montar_mensagens("Qual o prazo?", [doc("Prazo de {30} dias")])
    assert SEM_RESPOSTA in sistema.content
    assert "não ordens" in sistema.content
    assert "Prazo de {30} dias" in humano.content  # chaves do PDF não quebram o template
    assert humano.content.endswith("Pergunta: Qual o prazo?")


def test_sem_controle_remove_escapes_e_mantem_quebras():
    assert sem_controle("\x1b]0;titulo\x07\x1b[2Jlinha 1\nlinha\t2\x00") == "]0;titulo[2Jlinha 1\nlinha\t2"


def test_sem_controle_remove_invisiveis_e_marcas_de_direcao():
    # "relatório‮fdp.exe" aparece na tela como "relatórioexe.pdf"
    assert sem_controle("relatório‮fdp.exe") == "relatóriofdp.exe"
    assert sem_controle("infor­mação​ com﻿ BOM") == "informação com BOM"


def test_sem_controle_preserva_acentos_e_emoji():
    texto = "Férias, ação, São Paulo — 👨‍👩‍👧 ✓"
    assert sem_controle(texto) == texto
