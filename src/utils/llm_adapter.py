"""Adaptador de LLM/embeddings para no acoplarse a un proveedor concreto."""

from abc import ABC, abstractmethod
import logging
import time
from typing import List

from src.config import EMBEDDING_MODEL
from src.utils import get_openai_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str, model: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str], model: str) -> List[List[float]]:
        pass


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, model: str, system: str, user: str) -> str:
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed(self, text: str, model: str = EMBEDDING_MODEL) -> List[float]:
        client = get_openai_client()
        resp = client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding

    def embed_batch(
        self, texts: List[str], model: str = EMBEDDING_MODEL
    ) -> List[List[float]]:
        client = get_openai_client()
        out = []
        for text in texts:
            resp = client.embeddings.create(model=model, input=text)
            out.append(resp.data[0].embedding)
        return out


class OpenAILLMProvider(LLMProvider):
    def chat(self, model: str, system: str, user: str) -> str:
        client = get_openai_client()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=30,
            )
            elapsed = time.time() - start_time
            logger.info(f"LLM answered in {elapsed:.2f}s")
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.error(f"OpenAI call failed: {str(e)}")
            raise


def get_embedding(text: str, model: str | None = None) -> List[float]:
    """Función de conveniencia: un solo texto, usa EMBEDDING_MODEL por defecto."""
    from src.config import EMBEDDING_MODEL as DEFAULT_MODEL

    provider = OpenAIEmbeddingProvider()
    return provider.embed(text, model=model or DEFAULT_MODEL)


def get_embedding_provider() -> EmbeddingProvider:
    """Factory: hoy OpenAI; mañana puede ser otro según config."""
    return OpenAIEmbeddingProvider()


def get_llm_provider() -> LLMProvider:
    """Factory: hoy OpenAI; mañana puede ser otro según config."""
    return OpenAILLMProvider()
