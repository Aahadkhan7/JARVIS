import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

MAX_ITERATIONS = 6

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in .env file")