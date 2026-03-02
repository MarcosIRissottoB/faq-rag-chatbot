from src.config import EMBEDDING_MODEL
from src.utils import get_openai_client
from typing import List


def get_embedding(text: str, model: str | None = None) -> List[float]:
    client = get_openai_client()
    m = model or EMBEDDING_MODEL
    resp = client.embeddings.create(model=m, input=text)
    return resp.data[0].embedding
