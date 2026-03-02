import argparse
import json
import re
from src.constants import CHROMA_PATH, COLLECTION_NAME, MIN_CHUNK_SCORE_THRESHOLD
from src.config import MODEL_ANSWER, MODEL_EVAL
from src.utils.chroma_client import get_vector_store
from src.utils.llm_adapter import get_embedding_provider, get_llm_provider
from src.prompts import SYSTEM_PROMPT_ANSWER, SYSTEM_PROMPT_EVAL

def load_chroma_collection():
    """Conecta a ChromaDB en CHROMA_PATH y devuelve la colección 'faq'. Lanza si no existe."""
    try:
        store = get_vector_store()
        collection = store.get_collection(name=COLLECTION_NAME)
        return collection
    except Exception as e:
        raise RuntimeError(
            f"No se pudo cargar la colección '{COLLECTION_NAME}' en {CHROMA_PATH}. Ejecuta antes build_index.py. Detalle: {e}"
        ) from e

def search_similar_chunks(question, collection, top_k=5):
    """Embedea la pregunta, busca en Chroma por similitud y retorna list[dict] con 'text' y 'score' (2–5 chunks)."""
    top_k = max(2, min(5, int(top_k)))
    try:
        query_embedding = get_embedding_provider().embed(question)
    except Exception as e:
        raise RuntimeError(f"Error al obtener embedding de la pregunta: {e}") from e
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances"],
        )
    except Exception as e:
        raise RuntimeError(f"Error al buscar en ChromaDB: {e}") from e
    docs = results.get("documents", [[]])[0] or []
    dists = results.get("distances", [[]])[0] or []
    out = []
    for i, doc in enumerate(docs):
        d = dists[i] if i < len(dists) else 0.0
        raw_score = 1.0 - float(d)
        score = max(0.0, min(1.0, raw_score))
        out.append({"text": str(doc), "score": round(score, 6)})
    return out

def generate_answer(question, chunks):
    """Construye contexto desde chunks, llama modelo LLM y devuelve la respuesta en texto."""
    context = "\n\n".join(f"Chunk {i+1}:\n{c.get('text', '')}" for i, c in enumerate(chunks))
    user_content = f"""Contexto (chunks recuperados):

{context}

---

Pregunta del usuario: {question}

Responde usando solo el contexto de arriba.
"""
    try:
        return get_llm_provider().chat(
            model=MODEL_ANSWER,
            system=SYSTEM_PROMPT_ANSWER,
            user=user_content,
        )
    except Exception as e:
        raise RuntimeError(f"Error al generar respuesta: {e}") from e

def evaluate_response(question, answer, chunks):
    """Evalúa con el modelo LLM configurado y devuelve dict con 'score' (0–10) y 'reason' (>=50 caracteres)."""
    context = "\n\n".join(f"Chunk {i+1}:\n{c.get('text', '')}" for i, c in enumerate(chunks))
    user_content = f"""Pregunta del usuario: {question}

    Respuesta del sistema: {answer}

    Chunks de contexto usados:

    {context}

    Evalúa y devuelve solo un JSON con "score" (entero 0-10) y "reason" (string de al menos 50 caracteres)."""
    try:
        raw = get_llm_provider().chat(
            model=MODEL_EVAL,
            system=SYSTEM_PROMPT_EVAL,
            user=user_content,
        )
    except Exception as e:
        raise RuntimeError(f"Error al evaluar respuesta: {e}") from e
    try:
        json_str = re.sub(r"^.*?(\{.*\}).*$", r"\1", raw, flags=re.DOTALL)
        data = json.loads(json_str)
        reason = str(data.get("reason", ""))
        if len(reason) < 50:  
            reason = reason + " (Evaluación incompleta: el reason debe tener al menos 50 caracteres.)" if reason else "Evaluación no válida: reason con menos de 50 caracteres."
        return {"score": int(data.get("score", 0)), "reason": reason}
    except (json.JSONDecodeError, ValueError) as e:
        return {"score": 0, "reason": f"No se pudo parsear la evaluación: {e}. Raw: {raw[:200]}..."}

def main(question):
    """Orquesta: cargar colección, buscar chunks, generar respuesta y evaluar. Retorna el JSON del plan."""
    collection = load_chroma_collection()
    chunks = search_similar_chunks(question, collection)
    chunks_used = [c for c in chunks if c["score"] >= MIN_CHUNK_SCORE_THRESHOLD]
    if not chunks_used:
        chunks_used = chunks[:1]
    answer = generate_answer(question, chunks_used)
    eval_result = evaluate_response(question, answer, chunks_used)
    return {
        "user_question": question,
        "system_answer": answer,
        "chunks_related": chunks_used,
        "evaluation": eval_result,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Pregunta para el chatbot")
    args = parser.parse_args()
    result = main(args.question)
    print(json.dumps(result, ensure_ascii=False, indent=2))