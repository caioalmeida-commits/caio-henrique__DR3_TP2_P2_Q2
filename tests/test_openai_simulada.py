import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI

from app import service
from app.main import app, obter_cadeia

requisicoes = []


def criar_servidor_simulado() -> FastAPI:
    simulado = FastAPI()

    @simulado.post("/v1/chat/completions")
    async def completions(request: Request):
        corpo = await request.json()
        requisicoes.append(corpo)
        if "limite" in corpo["messages"][-1]["content"]:
            return JSONResponse({"error": {"message": "Rate limit reached", "type": "requests", "code": "rate_limit_exceeded"}}, status_code=429)
        return {
            "id": "chatcmpl-simulado",
            "object": "chat.completion",
            "created": 0,
            "model": corpo["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Bonjour le monde"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        }

    return simulado


@pytest.fixture(scope="module")
def url_da_openai_simulada():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    servidor = uvicorn.Server(uvicorn.Config(criar_servidor_simulado(), host="127.0.0.1", port=porta, log_level="error"))
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()
    while not servidor.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}/v1"
    servidor.should_exit = True
    thread.join()


@pytest.fixture(scope="module")
def client(url_da_openai_simulada):
    llm = ChatOpenAI(model="modelo-de-teste", base_url=url_da_openai_simulada, api_key="chave-de-teste", max_retries=0, timeout=5)
    app.dependency_overrides[obter_cadeia] = lambda: service.criar_cadeia(llm)
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def test_chatopenai_envia_o_prompt_e_le_a_resposta(client):
    requisicoes.clear()
    corpo = client.post("/traduzir", json={"texto": "Hello world"}).json()
    assert corpo["traducao"] == "Bonjour le monde"
    enviado = requisicoes[-1]
    assert enviado["model"] == "modelo-de-teste"
    assert enviado["messages"][0]["role"] == "system" and "francês" in enviado["messages"][0]["content"]
    assert enviado["messages"][-1] == {"role": "user", "content": "Hello world"}


def test_limite_da_openai_vira_429(client):
    assert client.post("/traduzir", json={"texto": "atingir o limite"}).status_code == 429
