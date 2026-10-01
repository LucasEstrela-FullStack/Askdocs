"""Configuração do AskDocs, lida das variáveis de ambiente e do .env."""

from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1"}


class Config(BaseSettings):
    """Parâmetros do pipeline. Cada campo aceita a variável ASKDOCS_<NOME>."""

    model_config = SettingsConfigDict(
        env_prefix="ASKDOCS_", env_file=".env", env_file_encoding="utf-8", extra="ignore",
        env_parse_none_str="",  # ASKDOCS_OLLAMA_NUM_GPU= vazio volta ao padrão do Ollama
    )

    pasta_base: Path = Path("base")
    pasta_db: Path = Path("db")
    colecao: str = "askdocs"

    ollama_url: str = "http://localhost:11434"
    # Camadas do modelo na GPU: None deixa o Ollama decidir, 0 força a CPU.
    ollama_num_gpu: int | None = Field(None, ge=0)
    # Segundos que o Ollama mantém o modelo carregado depois do último uso.
    # O padrão dele é 5 minutos; na CPU, recarregar custa de 5 a 15 s.
    ollama_keep_alive: int = Field(1800, ge=0)
    modelo_embedding: str = "bge-m3"
    modelo_chat: str = "llama3.2"
    temperatura: float = Field(0.1, ge=0, le=2)

    tamanho_chunk: int = Field(1000, gt=0)
    sobreposicao_chunk: int = Field(200, ge=0)

    k: int = Field(4, gt=0)
    # Medido com o bge-m3: perguntas que a base responde passam de 0.5,
    # perguntas de fora ficam perto de 0.25.
    limiar_relevancia: float = Field(0.4, ge=0, le=1)

    @model_validator(mode="after")
    def _validar_sobreposicao(self) -> "Config":
        if self.sobreposicao_chunk >= self.tamanho_chunk:
            raise ValueError("sobreposicao_chunk precisa ser menor que tamanho_chunk")
        return self

    @property
    def ollama_e_local(self) -> bool:
        return urlparse(self.ollama_url).hostname in HOSTS_LOCAIS
