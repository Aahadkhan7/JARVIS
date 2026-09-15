from langchain_groq import ChatGroq

from .config import GROQ_API_KEY, GROQ_MODEL
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS


def create_llm():

    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0,
    )


def create_agent():

    llm = create_llm()

    return llm.bind_tools(
        TOOLS
    )


def ask_jarvis(user_request: str):

    llm = create_agent()

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", user_request),
    ]

    response = llm.invoke(
        messages
    )

    return response