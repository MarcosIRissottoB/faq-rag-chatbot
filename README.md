# faq-rag-chatbot

FAQ Chatbot con RAG usando ChromaDB y OpenAI para soporte de HR SaaS.

## Descripción

Chatbot de preguntas frecuentes (FAQ) con RAG para HR SaaS: se construye un índice sobre un documento de FAQs en español, se realiza búsqueda por similitud sobre los fragmentos indexados y las respuestas se generan con GPT-4o-mini usando el contexto recuperado.

## Requisitos

- Python 3.11
- Cuenta OpenAI con API key

## Instalación

1. Entorno (crear y activar venv, opcional):
   `python3.11 -m venv .venv`
   `source .venv/bin/activate`

2. Instalar dependencias:
   `pip install -r requirements.txt`

3. Para ejecutar tests (opcional): `pip install -r requirements-dev.txt`

4. Copiar `.env.example` a `.env` y rellenar las 4 variables (OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, OPENAI_MODEL_ANSWER, OPENAI_MODEL_EVAL). Sin valores reales en el repo.
   `cp .env.example .env`

## Tests

Tests unitarios con **pytest** para `build_index` (load_and_chunk_document, generate_embeddings, save_to_chroma, index_already_loaded) y `query` (load_chroma_collection, search_similar_chunks, generate_answer, evaluate_response, main). No se requieren API keys reales: los tests usan mocks.

Desde la raíz del proyecto:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

En CI (GitHub Actions) los tests se ejecutan en cada push a `main`/`master` y en cada pull request.

## Cómo probar

1. **Construir el índice** (desde la raíz del proyecto):
   `python -m src.build_index`
   Para **reconstruir el índice** (por ejemplo tras cambiar el documento o la métrica de Chroma):  
   `python -m src.build_index --force`

2. Hacer una consulta:
   `python -m src.query --question "¿Qué pasos debo seguir en mi proceso de onboarding?"`

## Decisiones técnicas

- **Chunking:** ventana por palabras con overlap para no cortar frases y mantener contexto; tamaño 300 palabras y overlap 50 para equilibrar granularidad y coherencia.
- **Búsqueda:** similitud coseno sobre embeddings en ChromaDB (text-embedding-3-small) para recuperar los chunks más relevantes antes de generar la respuesta con el LLM.
- **Evaluación:** cada respuesta se evalúa con un score de 0 a 10 y un motivo (reason); el resultado se incluye en la salida JSON del CLI y en `outputs/sample_queries.json`.

## Estructura del proyecto

- `data/faq_document.txt`: documento fuente de FAQs (texto plano, ≥1000 palabras).
- `src/build_index.py`: script que carga el documento, lo divide en chunks, genera embeddings y guarda en ChromaDB.
- `src/query.py`: script que recibe una pregunta, busca chunks similares, genera la respuesta con el LLM y devuelve JSON (user_question, system_answer, chunks_related, evaluation).
- `outputs/sample_queries.json`: ejemplos de salida del pipeline de consultas (≥3 pares pregunta–respuesta).
- `chroma_db/`: directorio de persistencia de ChromaDB (generado al ejecutar build_index).
- `src/config.py`, `src/constants.py`: configuración y constantes.
- `src/utils/`: cliente ChromaDB y adaptador LLM/embeddings.
- `src/prompts/`: prompts del LLM (respuesta y evaluación).
- `docs/`: documentación (flujo de datos, decisiones RAG, prompts, checklist).
