"""Consulta: encontra na base os trechos relevantes para a pergunta."""

from langchain_chroma import Chroma
from langchain_core.documents import Document

from askdocs.config import Config


def filtrar_relevantes(
    resultados: list[tuple[Document, float]], limiar: float,
) -> list[tuple[Document, float]]:
    """Mantem os trechos com relevancia >= limiar, do mais para o menos relevante."""
    relevantes = [(doc, nota) for doc, nota in resultados if nota >= limiar]
    return sorted(relevantes, key=lambda par: par[1], reverse=True)


def buscar(pergunta: str, banco: Chroma, cfg: Config) -> list[tuple[Document, float]]:
    """Compara a pergunta com a base e devolve os ``k`` trechos mais parecidos.

    Trechos abaixo do limiar sao descartados: se nada sobrar, a base nao tem a
    resposta e o modelo nem precisa ser chamado, sem gastar tempo de CPU.
    """
    resultados = banco.similarity_search_with_relevance_scores(pergunta, k=cfg.k)
    return filtrar_relevantes(resultados, cfg.limiar_relevancia)
