import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app import service
from app.main import app, obter_cadeia

requisicao = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def usar_cadeia(cadeia):
    app.dependency_overrides[obter_cadeia] = lambda: cadeia


@pytest.fixture(autouse=True)
def limpar():
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def levantar(erro):
    def _falhar(_):
        raise erro

    return RunnableLambda(_falhar)


def test_traducao_com_fake_chat_model():
    usar_cadeia(service.criar_cadeia(FakeListChatModel(responses=["Bonjour le monde"])))
    corpo = client.post("/traduzir", json={"texto": "Hello world"}).json()
    assert corpo["texto_original"] == "Hello world"
    assert corpo["traducao"] == "Bonjour le monde"
    assert corpo["tempo_ms"] >= 0


def test_prompt_envia_o_texto_do_usuario():
    mensagens = service.PROMPT.invoke({"texto": "Hello"}).to_messages()
    assert mensagens[-1].content == "Hello"
    assert "francês" in mensagens[0].content


def test_sem_chave_devolve_503(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    obter_cadeia.cache_clear()
    resposta = client.post("/traduzir", json={"texto": "Hello"})
    assert resposta.status_code == 503


@pytest.mark.parametrize(
    "erro,status",
    [
        (RateLimitError("limite", response=httpx.Response(429, request=requisicao), body=None), 429),
        (APITimeoutError(request=requisicao), 504),
        (APIConnectionError(request=requisicao), 502),
    ],
)
def test_erros_da_openai_viram_codigos_http(erro, status):
    usar_cadeia(levantar(erro))
    assert client.post("/traduzir", json={"texto": "Hello"}).status_code == status


@pytest.mark.parametrize("corpo", [{}, {"texto": ""}, {"texto": "x" * 10001}])
def test_entradas_invalidas(corpo):
    usar_cadeia(service.criar_cadeia(FakeListChatModel(responses=["x"])))
    assert client.post("/traduzir", json=corpo).status_code == 422
