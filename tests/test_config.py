import pytest
from pydantic import ValidationError

from askdocs.config import Config

pytestmark = pytest.mark.usefixtures("env_limpo")


def test_padroes(cfg):
    assert cfg.modelo_embedding == "bge-m3"
    assert cfg.modelo_chat == "llama3.2"
    assert cfg.ollama_num_gpu is None
    assert cfg.ollama_e_local


def test_le_variaveis_com_prefixo(monkeypatch):
    monkeypatch.setenv("ASKDOCS_MODELO_CHAT", "qwen2.5:7b")
    monkeypatch.setenv("ASKDOCS_K", "6")
    cfg = Config(_env_file=None)
    assert (cfg.modelo_chat, cfg.k) == ("qwen2.5:7b", 6)


def test_variavel_vazia_volta_ao_padrao(monkeypatch):
    monkeypatch.setenv("ASKDOCS_OLLAMA_NUM_GPU", "")
    assert Config(_env_file=None).ollama_num_gpu is None


def test_sobreposicao_maior_que_chunk_e_invalida():
    with pytest.raises(ValidationError, match="sobreposicao_chunk"):
        Config(_env_file=None, tamanho_chunk=500, sobreposicao_chunk=500)


@pytest.mark.parametrize("campo, valor", [("limiar_relevancia", 1.5), ("k", 0), ("ollama_num_gpu", -1)])
def test_rejeita_valores_fora_da_faixa(campo, valor):
    with pytest.raises(ValidationError):
        Config(_env_file=None, **{campo: valor})


@pytest.mark.parametrize("url, local", [
    ("http://localhost:11434", True),
    ("http://127.0.0.1:11434", True),
    ("http://[::1]:11434", True),
    ("http://10.0.0.5:11434", False),
    ("https://ollama.exemplo.com", False),
])
def test_identifica_ollama_local(url, local):
    assert Config(_env_file=None, ollama_url=url).ollama_e_local is local
