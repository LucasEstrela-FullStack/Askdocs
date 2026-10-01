"""Configuracao central do AskDocs, lida de variaveis de ambiente e do .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Parametros do pipeline RAG. Cada campo aceita a variavel ASKDOCS_<NOME>."""

    model_config = SettingsConfigDict(
        env_prefix="ASKDOCS_", env_file=".env", env_file_encoding="utf-8", extra="ignore",
    )

    pasta_base: Path = Path("base")
    pasta_db: Path = Path("db")
    colecao: str = "askdocs"

    ollama_url: str = "http://localhost:11434"
    # Camadas do modelo enviadas a GPU; None deixa o Ollama decidir e 0 forca CPU.
    ollama_num_gpu: int | None = Field(None, ge=0)
    modelo_embedding: str = "bge-m3"
    modelo_chat: str = "llama3.2"
    temperatura: float = Field(0.1, ge=0, le=2)

    tamanho_chunk: int = Field(1000, gt=0)
    sobreposicao_chunk: int = Field(200, ge=0)

    k: int = Field(4, gt=0)
    limiar_relevancia: float = Field(0.5, ge=0, le=1)

    @model_validator(mode="after")
    def _validar_sobreposicao(self) -> "Config":
        if self.sobreposicao_chunk >= self.tamanho_chunk:
            raise ValueError("sobreposicao_chunk precisa ser menor que tamanho_chunk")
        return self


@lru_cache
def carregar_config() -> Config:
    return Config()
