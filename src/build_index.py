import sys
from pathlib import Path
import hashlib
from src.constants import (
    CHROMA_DISTANCE_METRIC,
    CHROMA_PATH,
    COLLECTION_NAME,
    DEFAULT_DOC_PATH,
)
from src.utils.llm_adapter import get_embedding_provider
from src.utils.chroma_client import get_vector_store


def index_already_loaded(client, doc_source_hash, num_chunks):
    """True si la colección existe, tiene el mismo número de chunks y el mismo hash del documento."""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return False
    if collection.count() != num_chunks:
        return False
    meta = collection.metadata or {}
    return meta.get("doc_source_hash") == doc_source_hash


def load_and_chunk_document(path, chunk_size=300, overlap=50):
    """Lee el documento en UTF-8, lo divide en ventanas de chunk_size palabras con overlap, valida y retorna lista de chunks."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Documento no encontrado: {path}")
    text = path.read_text(encoding="utf-8")
    words = text.split()
    if len(words) == 0:
        raise ValueError("El documento está vacío")
    step = chunk_size - overlap
    chunks = []
    for i in range(0, len(words), step):
        chunk_words = words[i : i + chunk_size]
        if not chunk_words:
            break
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
    validated_chunks = []
    for i, c in enumerate(chunks):
        num_words = len(c.split())
        est_tokens = num_words * 1.3
        if est_tokens < 50:
            print(f"Chunk {i} descartado por ser muy pequeño ({num_words} palabras)")
            continue
        if est_tokens > 500:
            raise ValueError(
                f"Chunk {i} excede 500 tokens estimados (estimado: {est_tokens:.0f} tokens). Ajusta el documento o los parámetros."
            )
        validated_chunks.append(c)
    if len(validated_chunks) < 20:
        raise ValueError(
            f"Se requieren al menos 20 chunks válidos; se generaron {len(validated_chunks)}. Aumenta el documento o ajusta chunk_size/overlap."
        )
    return validated_chunks


def generate_embeddings(chunks):
    """Genera embeddings con OpenAI text-embedding-3-small. Retorna lista de listas de float."""
    provider = get_embedding_provider()
    vectors = []
    for chunk in chunks:
        try:
            vectors.append(provider.embed(chunk))
        except Exception as e:
            raise RuntimeError(f"Error al obtener embedding (OpenAI/red): {e}") from e
    return vectors


def save_to_chroma(chunks, embeddings, doc_source_hash):
    """Persiste chunks y embeddings en ChromaDB (ruta local, colección faq)."""
    try:
        store = get_vector_store()
        try:
            store.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass
        collection = store.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "doc_source_hash": doc_source_hash,
                "hnsw:space": CHROMA_DISTANCE_METRIC,
            },
        )
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(ids=ids, documents=chunks, embeddings=embeddings)
    except Exception as e:
        raise RuntimeError(f"Error al guardar en ChromaDB: {e}") from e


def main(doc_path=None, force=False):
    """Orquesta: cargar y chunkear documento, generar embeddings, guardar en ChromaDB. Imprime resumen.
    No vuelve a cargar si el documento ya está en la DB y no cambió."""
    path = Path(doc_path or DEFAULT_DOC_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Documento no encontrado: {path}")
    doc_content = path.read_text(encoding="utf-8")
    doc_source_hash = hashlib.sha256(doc_content.encode()).hexdigest()
    chunks = load_and_chunk_document(path)
    store = get_vector_store()
    if not force and index_already_loaded(store, doc_source_hash, len(chunks)):
        print(
            f"Índice ya cargado (documento sin cambios). {len(chunks)} chunks en {CHROMA_PATH}. Usar --force para reconstruir."
        )
        return
    embeddings = generate_embeddings(chunks)
    save_to_chroma(chunks, embeddings, doc_source_hash)
    dim = len(embeddings[0]) if embeddings else 0
    print(
        f"Índice construido: {len(chunks)} chunks, dimensión del embedding {dim}, ChromaDB en {CHROMA_PATH}"
    )


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    path = args[0] if args else None
    force = "--force" in flags
    main(path, force=force)
