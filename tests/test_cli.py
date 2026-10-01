from types import SimpleNamespace

import pytest
from conftest import doc

from askdocs import cli
from askdocs.erros import ErroAskDocs
from askdocs.prompt import SEM_RESPOSTA


def ollama_com(*modelos):
    class Cliente:
        def __init__(self, host):
            pass

        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model=m) for m in modelos])

    return Cliente


class OllamaDesligado:
    def __init__(self, host):
        pass

    def list(self):
        raise ConnectionError("recusado")


def test_verificar_ollama_aceita_modelo_sem_tag(cfg, monkeypatch):
    monkeypatch.setattr(cli.ollama, "Client", ollama_com("bge-m3:latest", "qwen2.5:7b"))
    cli.verificar_ollama(cfg, "bge-m3", "qwen2.5:7b")


def test_verificar_ollama_explica_como_instalar_modelo(cfg, monkeypatch):
    monkeypatch.setattr(cli.ollama, "Client", ollama_com("bge-m3:latest"))
    with pytest.raises(ErroAskDocs, match="ollama pull llama3.2"):
        cli.verificar_ollama(cfg, "bge-m3", "llama3.2")


def test_verificar_ollama_desligado(cfg, monkeypatch):
    monkeypatch.setattr(cli.ollama, "Client", OllamaDesligado)
    with pytest.raises(ErroAskDocs, match="Ollama nao respondeu"):
        cli.verificar_ollama(cfg, "bge-m3")


class LlmFalso:
    def __init__(self):
        self.chamadas = 0

    def stream(self, mensagens):
        self.chamadas += 1
        yield SimpleNamespace(content="R$ 380,00 ")
        yield SimpleNamespace(content="por noite.")


def banco_com(*resultados):
    return SimpleNamespace(similarity_search_with_relevance_scores=lambda pergunta, k: list(resultados))


def test_sem_trecho_relevante_nao_chama_o_modelo(cfg, capsys):
    llm = LlmFalso()
    cli.responder("capital da Franca?", banco_com((doc("x"), 0.1)), llm, cfg)

    assert llm.chamadas == 0
    assert capsys.readouterr().out.strip() == SEM_RESPOSTA


def test_responde_e_agrupa_fontes_por_arquivo(cfg, capsys):
    banco = banco_com(
        (doc("a", "manual.pdf", 5), 0.9),
        (doc("b", "manual.pdf", 3), 0.8),
        (doc("c", "anexo.pdf", 1), 0.7),
        (doc("d", "manual.pdf", 5), 0.6),
    )
    cli.responder("limite?", banco, LlmFalso(), cfg)

    saida = capsys.readouterr().out
    assert "R$ 380,00 por noite." in saida
    assert "manual.pdf (p. 3, 5)" in saida
    assert "anexo.pdf (p. 1)" in saida


def test_resposta_e_fonte_nao_levam_sequencias_de_escape_ao_terminal(cfg, capsys):
    class LlmMalicioso:
        def stream(self, mensagens):
            yield SimpleNamespace(content="\x1b]0;titulo falso\x07\x1b[2JLimpo\n")

    banco = banco_com((doc("x", "\x1b[31mvermelho.pdf"), 0.9))
    cli.responder("?", banco, LlmMalicioso(), cfg)

    saida = capsys.readouterr().out
    assert "\x1b" not in saida and "\x07" not in saida
    assert "Limpo\n" in saida


@pytest.mark.parametrize("variavel", ["LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"])
def test_desliga_rastreamento_do_langsmith(cfg, monkeypatch, caplog, variavel):
    monkeypatch.setenv(variavel, "true")
    cli.garantir_execucao_local(cfg)
    assert cli.os.environ[variavel] == "false"
    assert "LangSmith" in caplog.text


def test_avisa_quando_o_ollama_e_remoto(cfg, caplog):
    cli.garantir_execucao_local(cfg.model_copy(update={"ollama_url": "http://10.0.0.5:11434"}))
    assert "vao sair desta maquina" in caplog.text


def test_ollama_local_nao_gera_aviso(cfg, caplog):
    cli.garantir_execucao_local(cfg)
    assert caplog.text == ""


def test_main_mostra_erro_amigavel_sem_traceback(monkeypatch, capsys):
    def falha(cfg, pergunta):
        raise ErroAskDocs("base vazia")

    monkeypatch.setattr("sys.argv", ["askdocs", "perguntar", "oi"])
    monkeypatch.setattr(cli, "cmd_perguntar", falha)

    with pytest.raises(SystemExit) as saida:
        cli.main()

    assert saida.value.code == 1
    assert capsys.readouterr().err.strip() == "erro: base vazia"
