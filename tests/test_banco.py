import pytest
from conftest import doc
from langchain_core.embeddings import DeterministicFakeEmbedding

from askdocs import banco
from askdocs.banco import abrir_banco, id_do_chunk, indexar


class EmbeddingQueFalha(DeterministicFakeEmbedding):
    def embed_documents(self, texts):
        raise RuntimeError("Ollama caiu")


@pytest.fixture
def embeddings_falsos(monkeypatch):
    """Troca o Ollama por embeddings deterministicos: mesmo texto, mesmo vetor."""
    monkeypatch.setattr(banco, "OllamaEmbeddings", lambda **_: DeterministicFakeEmbedding(size=32))


def chunks():
    return [
        doc("Hospedagem ate R$ 380 por noite", pagina=5, start_index=0),
        doc("Senhas com no minimo 14 caracteres", pagina=5, start_index=400),
        doc("Ferias pedidas com 45 dias de antecedencia", pagina=3, start_index=0),
    ]


def test_id_do_chunk_e_estavel_e_unico():
    a, b, c = chunks()
    assert id_do_chunk(a) == id_do_chunk(doc("outro texto", pagina=5, start_index=0))
    assert len({id_do_chunk(a), id_do_chunk(b), id_do_chunk(c)}) == 3


def test_indexa_e_encontra_o_trecho_identico(cfg, embeddings_falsos):
    assert indexar(chunks(), cfg) == 3

    [(achado, nota)] = abrir_banco(cfg).similarity_search_with_relevance_scores(
        "Senhas com no minimo 14 caracteres", k=1,
    )
    assert achado.metadata == {"fonte": "a.pdf", "pagina": 5, "start_index": 400}
    assert nota == pytest.approx(1, abs=1e-3)


def test_reindexar_substitui_em_vez_de_duplicar(cfg, embeddings_falsos):
    indexar(chunks(), cfg)
    indexar(chunks()[:1], cfg)
    assert abrir_banco(cfg)._collection.count() == 1


def test_informa_progresso(cfg, embeddings_falsos, monkeypatch):
    monkeypatch.setattr(banco, "LOTE_EMBEDDING", 2)
    passos = []
    indexar(chunks(), cfg, lambda feitos, total: passos.append((feitos, total)))
    assert passos == [(2, 3), (3, 3)]


def test_falha_do_ollama_preserva_a_base_anterior(cfg, embeddings_falsos, monkeypatch):
    indexar(chunks(), cfg)
    monkeypatch.setattr(banco, "OllamaEmbeddings", lambda **_: EmbeddingQueFalha(size=32))

    with pytest.raises(RuntimeError):
        indexar(chunks()[:1], cfg)

    monkeypatch.setattr(banco, "OllamaEmbeddings", lambda **_: DeterministicFakeEmbedding(size=32))
    assert abrir_banco(cfg)._collection.count() == 3
