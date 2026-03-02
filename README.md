# faq-rag-chatbot

FAQ Chatbot con RAG usando ChromaDB y OpenAI para soporte de HR SaaS.

## Descripción

Chatbot de preguntas frecuentes (FAQ) con RAG para HR SaaS: se construye un índice sobre un documento de FAQs en español, se realiza búsqueda por similitud sobre los fragmentos indexados y las respuestas se generan con GPT-4o-mini usando el contexto recuperado.

## Requisitos

- Python 3.11
- Cuenta OpenAI con API key

## Instalación

1. **Crear y activar el entorno virtual** (recomendado):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

   Si tienes Python 3.11: `python3.11 -m venv .venv`. Si no, `python3` (3.9+) suele bastar.

2. **Instalar dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Copiar `.env.example` a `.env`** y rellenar las variables (OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, OPENAI_MODEL_ANSWER, OPENAI_MODEL_EVAL). Sin valores reales en el repo.
   ```bash
   cp .env.example .env
   ```

## Tests

El proyecto incluye **tests unitarios** con pytest para los módulos `build_index` y `query`. No se necesitan API keys reales: los tests usan mocks.

**Cómo ejecutar los tests** (desde la raíz del proyecto, con el venv activado):

1. Instalar dependencias de test (solo la primera vez):

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Ejecutar todos los tests:

   ```bash
   pytest tests/ -v
   ```

   Si el comando `pytest` no se encuentra: `python3 -m pytest tests/ -v`

3. Si falla el import por falta de `.env`, puedes usar variables dummy solo para los tests:
   ```bash
   OPENAI_API_KEY=sk-fake OPENAI_MODEL_ANSWER=gpt-4o-mini OPENAI_MODEL_EVAL=gpt-4o-mini OPENAI_EMBEDDING_MODEL=text-embedding-3-small pytest tests/ -v
   ```

**Qué se prueba:** `build_index` (load_and_chunk_document, generate_embeddings, save_to_chroma, index_already_loaded) y `query` (load_chroma_collection, search_similar_chunks, generate_answer, evaluate_response, main).

## Desarrollo (linting y formato)

El proyecto usa **ruff** (linting), **black** (formato) y **mypy** (tipado). Para tener estos comandos disponibles, instala las dependencias de desarrollo (igual que para los tests):

```bash
pip install -r requirements-dev.txt
```

Comandos útiles:

- **Linting con ruff** (recomendado antes de hacer commit):
  ```bash
  ruff check . --fix
  ```
- **Formato con black:** `black .`
- **Pre-commit:** si instalas los hooks con `pre-commit install`, ruff y black se ejecutan automáticamente al hacer commit (ver `.pre-commit-config.yaml`).

## CI (GitHub Actions)

Los tests se ejecutan automáticamente en **GitHub Actions** en cada:

- **Push** a las ramas `main` o `master`
- **Pull request** hacia `main` o `master`

**Cómo comprobarlo:** en el repositorio, pestaña **Actions** → workflow **Tests** → ver el último run. Si el job termina en verde, los tests pasaron en CI. También puedes abrir un PR y ver el estado del workflow en la página del PR.

**Antes de hacer push:** para evitar que falle el CI sin haber probado, ejecuta en local los mismos pasos que el workflow (Debug imports + pytest). Ver [docs/CI.md](docs/CI.md) sección **"Antes de push: validar en local"** (venv con Python 3.11, `pip install -r requirements.txt -r requirements-dev.txt`, `pip install -e .`, luego `./scripts/simulate_ci_debug.sh`).

**Si el workflow falla** (p. ej. "Process completed with exit code 2"): ver [docs/CI.md](docs/CI.md) para códigos de salida de pytest, cómo ver el log completo del paso "Run tests" y los ajustes aplicados en este repo.

## Cómo probar

1. **Construir el índice** (desde la raíz del proyecto):
   `python -m src.build_index`
   Si el índice ya está creado y el documento no ha cambiado, verás el mensaje *"Índice ya cargado (documento sin cambios)...";* en ese caso no se reconstruye a menos que uses `--force`.
   Para **reconstruir el índice** (por ejemplo tras cambiar el documento o la métrica de Chroma):  
   `python -m src.build_index --force`

   **Chunking (por defecto, sin flags):** se toma de `src/constants.py` usando `CHUNK_SIZE_DEFAULT` y `CHUNK_OVERLAP_DEFAULT`.
   Si quieres cambiar los defaults para no pasar flags en cada ejecución, edita esos valores en `src/constants.py`.

   **Override opcional por CLI (si necesitas probar valores puntuales):**
   `python -m src.build_index --chunk-size 250 --chunk-overlap 50`

2. Hacer una consulta:
   `python -m src.query --question "¿Qué pasos debo seguir en mi proceso de onboarding?"`

## Decisiones técnicas

- **Chunking:** ventana por palabras con overlap para no cortar frases y mantener contexto; tamaño 300 palabras y overlap 50 para equilibrar granularidad y coherencia.
- **Búsqueda:** similitud coseno sobre embeddings en ChromaDB (text-embedding-3-small) para recuperar los chunks más relevantes antes de generar la respuesta con el LLM.
- **Evaluación:** cada respuesta se evalúa con un score de 0 a 10 y un motivo (reason); el resultado se incluye en la salida JSON del CLI y en `outputs/sample_queries.json`.
- **Logging y resiliencia en llamadas LLM:** en `src/query.py` y `src/utils/llm_adapter.py` se configura logging por módulo (StreamHandler, formato con timestamp y nivel). Las llamadas al LLM se miden en tiempo (log de duración en segundos), tienen timeout de 30 s en el adaptador y, ante fallo, se registra el error con `logger.error` antes de relanzar la excepción, evitando que la app se caiga sin traza.

## Estructura del proyecto

- `data/faq_document.txt`: documento fuente de FAQs (texto plano, ≥1000 palabras).
- `src/build_index.py`: script que carga el documento, lo divide en chunks, genera embeddings y guarda en ChromaDB.
- `src/query.py`: script que recibe una pregunta, busca chunks similares, genera la respuesta con el LLM y devuelve JSON (user_question, system_answer, chunks_related, evaluation); incluye logging y medición de tiempo en las llamadas al LLM.
- `outputs/sample_queries.json`: ejemplos de salida del pipeline de consultas (≥3 pares pregunta–respuesta).
- `chroma_db/`: directorio de persistencia de ChromaDB (generado al ejecutar build_index).
- `src/config.py`, `src/constants.py`: configuración y constantes.
- `src/utils/`: cliente ChromaDB y adaptador LLM/embeddings (en `llm_adapter.py`: timeout 30 s y logging de llamadas y errores).
- `src/prompts/`: prompts del LLM (respuesta y evaluación).
- `tests/`: tests unitarios (pytest) para `build_index` y `query`; `requirements-dev.txt` para dependencias de test.
- `pyproject.toml`: definición del proyecto e instalación editable (`pip install -e .`) para CI y desarrollo.
- `.github/workflows/test.yml`: workflow de CI que ejecuta los tests en cada push y en cada pull request.
- `docs/`: documentación (flujo de datos, decisiones RAG, prompts, checklist, **CI.md** para troubleshooting de GitHub Actions).
