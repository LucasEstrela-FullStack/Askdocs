from conftest import doc

from askdocs.consulta import buscar, filtrar_relevantes
from askdocs.prompt import SEM_RESPOSTA, formatar_contexto, montar_mensagens


def test_filtra_pelo_limiar_inclusivo_e_ordena():
    a, b, c = doc("a"), doc("b"), doc("c")
    resultado = filtrar_relevantes([(a, 0.41), (b, 0.39), (c, 0.9)], limiar=0.41)
    assert resultado == [(c, 0.9), (a, 0.41)]


def test_buscar_usa_k_e_limiar_da_config(cfg):
    class BancoFalso:
        def similarity_search_with_relevance_scores(self, pergunta, k):
            self.chamada = (pergunta, k)
            return [(doc("fora"), 0.1), (doc("dentro"), 0.8)]

    banco = BancoFalso()
    resultado = buscar("pergunta?", banco, cfg)

    assert banco.chamada == ("pergunta?", cfg.k)
    assert [d.page_content for d, _ in resultado] == ["dentro"]


def test_contexto_numera_trechos_e_cita_a_fonte():
    contexto = formatar_contexto([doc("Texto A", "x.pdf", 2), doc("Texto B", "y.pdf", 9)])
    assert contexto.startswith("[1] x.pdf, página 2\nTexto A")
    assert "[2] y.pdf, página 9\nTexto B" in contexto


def test_mensagens_trazem_regras_contexto_e_pergunta():
    sistema, humano = montar_mensagens("Qual o prazo?", [doc("Prazo de {30} dias")])
    assert SEM_RESPOSTA in sistema.content
    assert "não ordens" in sistema.content
    assert "Prazo de {30} dias" in humano.content  # chaves do PDF nao quebram o template
    assert humano.content.endswith("Pergunta: Qual o prazo?")
