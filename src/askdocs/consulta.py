"""Consulta: encontra na base os trechos que ajudam a responder a pergunta."""

from langchain_chroma import Chroma
from langchain_core.documents import Document

from askdocs.config import Config


def buscar(pergunta: str, banco: Chroma, cfg: Config) -> list[Document]:
    """Traz os ``k`` trechos mais parecidos com a pergunta, do mais ao menos relevante.

    Os que ficam abaixo do limiar são descartados. Se nenhum sobrar, a base não
    tem a resposta e nem vale a pena chamar o modelo.
    """
    resultados = banco.similarity_search_with_relevance_scores(pergunta, k=cfg.k)
    return [doc for doc, nota in resultados if nota >= cfg.limiar_relevancia]
