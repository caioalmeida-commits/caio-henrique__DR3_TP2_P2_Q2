import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

MODELO_PADRAO = "gpt-6-luna"

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "Você é um tradutor profissional. Traduza o texto do usuário do inglês para o francês. Responda somente com a tradução."),
        ("human", "{texto}"),
    ]
)


def nome_do_modelo() -> str:
    return os.getenv("OPENAI_MODEL", MODELO_PADRAO)


def criar_cadeia(llm=None):
    llm = llm or ChatOpenAI(model=nome_do_modelo(), timeout=30, max_retries=2)
    return PROMPT | llm | StrOutputParser()
