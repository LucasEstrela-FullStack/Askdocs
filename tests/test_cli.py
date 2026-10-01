from types import SimpleNamespace

import ollama
import pytest
from conftest import doc
from langchain_core.tracers.context import _tracing_v2_is_enabled
from langsmith.utils import get_env_var

from askdocs import banco, cli, modelos
from askdocs.erros import ErroAskDocs
from askdocs.prompt import SEM_RESPOSTA


def ollama_com(*modelos_instalados, erro=None):
    class Cliente:
        def __init__(self, host):
            pass

        def list(self):
            if erro:
                raise erro
            return SimpleNamespace(models=[SimpleNamespace(model=m) for m in modelos_instalados])

    return Cliente


def test_verificar_ollama_aceita_modelo_sem_tag(cfg, monkeypatch):
    monkeypatch.setattr(modelos.ollama, "Client", ollama_com("bge-m3:latest", "qwen2.5:7b"))
    modelos.verificar_ollama(cfg, "bge-m3", "qwen2.5:7b")


def test_verificar_ollama_explica_como_instalar_modelo(cfg, monkeypatch):
    monkeypatch.setattr(modelos.ollama, "Client", ollama_com("bge-m3:latest"))
    with pytest.raises(ErroAskDocs, match="ollama pull llama3.2"):
        modelos.verificar_ollama(cfg, "bge-m3", "llama3.2")


def test_verificar_ollama_desligado(cfg, monkeypatch):
    monkeypatch.setattr(modelos.ollama, "Client", ollama_com(erro=ConnectionError("recusado")))
    with pytest.raises(ErroAskDocs, match="não respondeu"):
        modelos.verificar_ollama(cfg, "bge-m3")


@pytest.fixture
def langsmith_ligado(monkeypatch):
    # O langsmith guarda as variáveis em cache: limpar antes e depois evita
    # que o teste passe por acaso ou vaze para os outros.
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    get_env_var.cache_clear()
    yield
    monkeypatch.undo()
    get_env_var.cache_clear()


def test_execucao_local_desliga_langsmith_mesmo_com_a_variavel_ligada(cfg, langsmith_ligado):
    assert _tracing_v2_is_enabled()
    with modelos.execucao_local(cfg):
        assert not _tracing_v2_is_enabled()


def test_execucao_local_avisa_quando_o_ollama_e_remoto(cfg, caplog):
    with modelos.execucao_local(cfg.model_copy(update={"ollama_url": "http://10.0.0.5:11434"})):
        pass
    assert "sair desta máquina" in caplog.text


def test_execucao_local_sem_aviso_com_ollama_local(cfg, caplog):
    with modelos.execucao_local(cfg):
        pass
    assert caplog.text == ""


class LlmFalso:
    def __init__(self, *partes):
        self.partes = partes or ("R$ 380,00 ", "por noite.")
        self.chamadas = 0

    def stream(self, mensagens):
        self.chamadas += 1
        yield from (SimpleNamespace(content=p) for p in self.partes)


def banco_com(*resultados):
    return SimpleNamespace(similarity_search_with_relevance_scores=lambda pergunta, k: list(resultados))


def test_sem_trecho_relevante_nao_chama_o_modelo(cfg, capsys):
    llm = LlmFalso()
    cli.responder("capital da França?", banco_com((doc("x"), 0.1)), llm, cfg)

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


def test_resposta_do_modelo_nao_leva_escapes_ao_terminal(cfg, capsys):
    llm = LlmFalso("\x1b]0;titulo falso\x07", "\x1b[2JLimpo")
    cli.responder("?", banco_com((doc("x"), 0.9)), llm, cfg)

    saida = capsys.readouterr().out
    assert "\x1b" not in saida and "\x07" not in saida
    assert "Limpo" in saida


def test_nao_cita_fontes_quando_o_modelo_nao_acha_a_resposta(cfg, capsys):
    llm = LlmFalso("Não encontrei essa ", "informação nos documentos.")
    cli.responder("qual o CEP?", banco_com((doc("x", "manual.pdf", 2), 0.9)), llm, cfg)

    saida = capsys.readouterr().out
    assert SEM_RESPOSTA in saida
    assert "Fontes" not in saida and "manual.pdf" not in saida


def test_modo_conversa_continua_depois_de_falha_do_ollama(cfg, monkeypatch, capsys):
    monkeypatch.setattr(modelos, "verificar_ollama", lambda *a: None)
    monkeypatch.setattr(modelos, "criar_llm", lambda cfg: "llm")
    monkeypatch.setattr(banco, "total_de_chunks", lambda cfg: 3)
    monkeypatch.setattr(banco, "modelo_da_base", lambda cfg: cfg.modelo_embedding)
    monkeypatch.setattr(banco, "abrir_banco", lambda cfg: "banco")

    entradas = iter(["primeira", "segunda", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    respondidas = []

    def responder(pergunta, *_):
        respondidas.append(pergunta)
        if pergunta == "primeira":
            raise ollama.ResponseError("llama-server process has terminated")
        print("ok")

    monkeypatch.setattr(cli, "responder", responder)
    cli.cmd_perguntar(cfg, None)

    assert respondidas == ["primeira", "segunda"]
    saida = capsys.readouterr()
    assert "llama-server process has terminated" in saida.err
    assert "ok" in saida.out


def test_main_mostra_erro_amigavel_sem_traceback(monkeypatch, capsys):
    def falha(cfg, pergunta):
        raise ErroAskDocs("base vazia")

    monkeypatch.setattr("sys.argv", ["askdocs", "perguntar", "oi"])
    monkeypatch.setattr(cli, "cmd_perguntar", falha)

    with pytest.raises(SystemExit) as saida:
        cli.main()

    assert saida.value.code == 1
    assert capsys.readouterr().err.strip() == "erro: base vazia"
