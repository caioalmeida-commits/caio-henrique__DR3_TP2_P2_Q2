from pydantic import BaseModel, Field


class TraducaoRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=10000, description="Texto em inglês", examples=["Good morning! How are you today?"])


class TraducaoResponse(BaseModel):
    texto_original: str
    traducao: str
    modelo: str
    tempo_ms: float
