import os
from dotenv import load_dotenv

load_dotenv()

def _required(key: str, label: str) -> str:
    val = os.getenv(key)
    if not val or not str(val).strip():
        raise ValueError(
            f"{label} no está configurada. Define {key} en .env (ej. {key}=gpt-4o-mini)."
        )
    return val.strip()

OPENAI_API_KEY = _required("OPENAI_API_KEY", "OPENAI_API_KEY")
MODEL_ANSWER = _required("OPENAI_MODEL_ANSWER", "OPENAI_MODEL_ANSWER")
MODEL_EVAL = _required("OPENAI_MODEL_EVAL", "OPENAI_MODEL_EVAL")
EMBEDDING_MODEL = _required("OPENAI_EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL")