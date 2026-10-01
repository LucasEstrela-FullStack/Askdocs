"""Ponta a ponta com o Ollama de verdade. Lento na CPU; rode com: uv run pytest -m integracao"""

import runpy
from pathlib import Path

import pytest
from langchain_ollama import ChatOllama

from askdocs import cli
from askdocs.banco import abrir_banco
from askdocs.config import Config
from askdocs.prompt import SEM_RESPOSTA

pytestmark = pytest.mark.integracao

SCRIPT_PDF = Path(__file__).parent.parent / "scripts" / "gerar_pdf_exemplo.py"


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("integracao")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sys.argv", ["gerar", str(pasta / "base" / "manual.pdf")])
        runpy.run_path(str(SCRIPT_PDF), run_name="__main__")

    # Le o .env do projeto (ex.: ASKDOCS_OLLAMA_NUM_GPU=0), mas usa pastas temporarias.
    cfg = Config(pasta_base=pasta / "base", pasta_db=pasta / "db")
    cli.cmd_indexar(cfg)
    llm = ChatOllama(
        model=cfg.modelo_chat, base_url=cfg.ollama_url, temperature=0, num_gpu=cfg.ollama_num_gpu,
    )
    return cfg, abrir_banco(cfg), llm


@pytest.mark.parametrize("pergunta, esperado", [
    ("Qual o limite de hospedagem por noite em viagem?", "380"),
    ("Com quantos dias de antecedência devo pedir férias?", "45"),
    ("Quantos caracteres a senha precisa ter no mínimo?", "14"),
])
def test_responde_com_dados_do_pdf(ambiente, capsys, pergunta, esperado):
    cfg, banco, llm = ambiente
    cli.responder(pergunta, banco, llm, cfg)
    saida = capsys.readouterr().out
    assert esperado in saida
    assert "manual.pdf" in saida


def test_recusa_pergunta_fora_da_base(ambiente, capsys):
    cfg, banco, llm = ambiente
    cli.responder("Qual a capital da França?", banco, llm, cfg)
    assert SEM_RESPOSTA in capsys.readouterr().out
