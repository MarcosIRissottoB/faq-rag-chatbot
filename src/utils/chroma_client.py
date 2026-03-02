"""Cliente Chroma y adaptador de vector store para poder cambiar de backend sin tocar lógica de negocio."""
import logging
from typing import Optional
from src.constants import CHROMA_PATH

import chromadb
from chromadb.config import Settings

logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

class VectorStoreAdapter:
    """Interfaz del store de vectores. Implementaciones: ChromaVectorStore, (futuro OtroStore)."""

    def get_collection(self, name: str):
        raise NotImplementedError

    def get_or_create_collection(self, name: str, metadata: Optional[dict] = None):
        raise NotImplementedError

    def delete_collection(self, name: str) -> None:
        raise NotImplementedError

class ChromaVectorStore(VectorStoreAdapter):
    """Implementación usando Chroma. Hoy usamos esta; mañana puede existir otra (Pinecone, etc.)."""

    def __init__(self, path: str = CHROMA_PATH):
        self._client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )

    def get_collection(self, name: str):
        return self._client.get_collection(name=name)

    def get_or_create_collection(self, name: str, metadata: Optional[dict] = None):
        return self._client.get_or_create_collection(name=name, metadata=metadata or {})

    def delete_collection(self, name: str) -> None:
        try:
            self._client.delete_collection(name=name)
        except Exception:
            pass

def get_vector_store() -> VectorStoreAdapter:
    """Factory: hoy devuelve Chroma; mañana puede devolver otro adaptador según config."""
    return ChromaVectorStore(path=CHROMA_PATH)