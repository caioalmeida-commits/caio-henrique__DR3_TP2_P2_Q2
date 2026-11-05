import os
import time
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app import service
from app.schemas import TraducaoRequest, TraducaoResponse

app = FastAPI(
    title="Tradução inglês-francês com OpenAI e LangChain",
    description="Recebe um texto em inglês e devolve a tradução para o francês usando um modelo da OpenAI por meio do LangChain.",
    version="1.0.0",
)


@lru_cache
def obter_cadeia():
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada")
    return service.criar_cadeia()


@app.get("/health", summary="Estado da API")
def health():
    return {"status": "ok", "modelo": service.nome_do_modelo(), "chave_configurada": bool(os.getenv("OPENAI_API_KEY"))}


@app.post("/traduzir", response_model=TraducaoResponse, summary="Traduz um texto do inglês para o francês")
async def traduzir(dados: TraducaoRequest, cadeia=Depends(obter_cadeia)):
    inicio = time.perf_counter()
    try:
        traducao = await cadeia.ainvoke({"texto": dados.texto})
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Limite de uso da API da OpenAI atingido")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="A API da OpenAI demorou demais para responder")
    except APIConnectionError:
        raise HTTPException(status_code=502, detail="Falha de conexão com a API da OpenAI")
    except APIStatusError as erro:
        raise HTTPException(status_code=502, detail=f"A API da OpenAI retornou o erro {erro.status_code}")
    return TraducaoResponse(
        texto_original=dados.texto,
        traducao=traducao.strip(),
        modelo=service.nome_do_modelo(),
        tempo_ms=round((time.perf_counter() - inicio) * 1000, 1),
    )
