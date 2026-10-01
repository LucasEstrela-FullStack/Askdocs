import pytest
from conftest import doc
from langchain_core.embeddings import DeterministicFakeEmbedding

from askdocs import banco
from askdocs.banco import abrir_banco, id_do_chunk, indexar, modelo_da_base, total_de_chunks


class EmbeddingQueFalha(DeterministicFakeEmbedding):
    def embed_documents(self, texts):
        raise RuntimeError("Ollama caiu")


class EmbeddingQueConta(DeterministicFakeEmbedding):
    textos: list[str] = []

    def embed_documents(self, texts):
        self.textos.extend(texts)
        return super().embed_documents(texts)


def usar_embeddings(monkeypatch, classe=DeterministicFakeEmbedding):
    """Troca o Ollama por embeddings determinísticos: mesmo texto, mesmo vetor."""
    modelo = classe(size=32)
    monkeypatch.setattr(banco, "criar_embeddings", lambda cfg: modelo)
    return modelo


@pytest.fixture(autouse=True)
def embeddings_falsos(monkeypatch):
    return usar_embeddings(monkeypatch)


def chunks():
    return [
        doc("Hospedagem até R$ 380 por noite", pagina=5, start_index=0),
        doc("Senhas com no mínimo 14 caracteres", pagina=5, start_index=400),
        doc("Férias pedidas com 45 dias de antecedência", pagina=3, start_index=0),
    ]


def test_id_muda_com_o_texto_e_e_unico_por_posicao():
    a, b, c = chunks()
    assert id_do_chunk(a) == id_do_chunk(doc(a.page_content, pagina=5, start_index=0))
    assert id_do_chunk(a) != id_do_chunk(doc("Hospedagem até R$ 400 por noite", pagina=5, start_index=0))
    assert len({id_do_chunk(a), id_do_chunk(b), id_do_chunk(c)}) == 3


def test_indexa_e_encontra_o_trecho_identico(cfg):
    assert indexar(chunks(), cfg) == (3, 0, 3)

    [(achado, nota)] = abrir_banco(cfg).similarity_search_with_relevance_scores(
        "Senhas com no mínimo 14 caracteres", k=1,
    )
    assert achado.metadata == {"fonte": "a.pdf", "pagina": 5, "start_index": 400}
    assert nota == pytest.approx(1, abs=1e-3)
    assert modelo_da_base(cfg) == cfg.modelo_embedding


def test_reindexar_sem_mudancas_nao_gera_embeddings(cfg, monkeypatch):
    indexar(chunks(), cfg)
    contador = usar_embeddings(monkeypatch, EmbeddingQueConta)

    assert indexar(chunks(), cfg) == (0, 0, 3)
    assert contador.textos == []


def test_reindexar_troca_o_que_mudou_e_remove_o_que_sumiu(cfg, monkeypatch):
    indexar(chunks(), cfg)
    contador = usar_embeddings(monkeypatch, EmbeddingQueConta)
    editado = doc("Hospedagem até R$ 400 por noite", pagina=5, start_index=0)

    assert indexar([editado, chunks()[1]], cfg) == (1, 2, 2)
    assert contador.textos == [editado.page_content]
    assert total_de_chunks(cfg) == 2


def test_trocar_o_modelo_de_embedding_refaz_a_base(cfg):
    indexar(chunks(), cfg)
    outro = cfg.model_copy(update={"modelo_embedding": "outro-modelo"})

    assert indexar(chunks(), outro) == (3, 0, 3)
    assert modelo_da_base(outro) == "outro-modelo"


def test_informa_progresso(cfg, monkeypatch):
    monkeypatch.setattr(banco, "LOTE_EMBEDDING", 2)
    passos = []
    indexar(chunks(), cfg, lambda feitos, total: passos.append((feitos, total)))
    assert passos == [(2, 3), (3, 3)]


@pytest.mark.parametrize("modelo", ["bge-m3", "outro-modelo"])
def test_falha_do_ollama_preserva_a_base(cfg, monkeypatch, modelo):
    indexar(chunks(), cfg)
    usar_embeddings(monkeypatch, EmbeddingQueFalha)

    with pytest.raises(RuntimeError):
        indexar([doc("texto novo", start_index=9)], cfg.model_copy(update={"modelo_embedding": modelo}))

    assert total_de_chunks(cfg) == 3
