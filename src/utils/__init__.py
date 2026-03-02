from openai import OpenAI
from src.config import OPENAI_API_KEY
def get_openai_client():
    api_key = OPENAI_API_KEY
    if not api_key or not api_key.strip():
        raise ValueError("OPENAI_API_KEY no está configurada. Configura .env y vuelve a ejecutar.")
    return OpenAI(api_key=api_key)