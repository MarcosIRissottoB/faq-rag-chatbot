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

## Probar localmente

Todo desde la **raíz del proyecto**, con el **entorno virtual activado** (y `.env` configurado si vas a usar `build_index` o `query`).

### 1. Ejecutar los tests

El proyecto incluye tests unitarios (pytest) para `build_index` y `query`. No se necesitan API keys reales: los tests usan mocks.

- Instalar dependencias de test (solo la primera vez):
  ```bash
  pip install -r requirements-dev.txt
  ```
- Ejecutar todos los tests:
  ```bash
  pytest tests/ -v
  ```
  Si `pytest` no se encuentra: `python3 -m pytest tests/ -v`
- Si falla el import por falta de `.env`, usá variables dummy solo para tests:
  ```bash
  OPENAI_API_KEY=sk-fake OPENAI_MODEL_ANSWER=gpt-4o-mini OPENAI_MODEL_EVAL=gpt-4o-mini OPENAI_EMBEDDING_MODEL=text-embedding-3-small pytest tests/ -v
  ```

### 2. Construir el índice

```bash
python -m src.build_index
```

Si el índice ya existe y el documento no cambió, verás *"Índice ya cargado (documento sin cambios)..."*. Para **reconstruir**: `python -m src.build_index --force`.

Opcional (override de chunking): `python -m src.build_index --chunk-size 250 --chunk-overlap 50`. Los valores por defecto están en `src/constants.py`.

### 3. Hacer una consulta

```bash
python -m src.query --question "¿Qué pasos debo seguir en mi proceso de onboarding?"
```

La salida es JSON (pregunta, respuesta, chunks usados, evaluación).

### Solución de problemas (local)

- **`no such column: collections.topic`** al ejecutar `build_index` o `query`: la base de ChromaDB en `./chroma_db` tiene un esquema antiguo. Borrá la carpeta y volvé a construir el índice:
  ```bash
  rm -rf ./chroma_db
  python -m src.build_index
  ```
- **`Client.__init__() got an unexpected keyword argument 'proxies'`**: incompatibilidad entre la librería `openai` y versiones recientes de `httpx`. El proyecto fija `httpx<0.28` en `requirements.txt`. Asegurate de instalar con `pip install -r requirements.txt` en un entorno limpio.

---

## Probar con Docker

Podés construir una imagen y ejecutar tests o los comandos del proyecto **sin instalar dependencias en tu máquina**. La API key no va en el Dockerfile; se pasa al ejecutar el contenedor (`-e OPENAI_API_KEY=...`).

### 1. Construir la imagen

Desde la raíz del proyecto:

```bash
docker build -t faq-rag-chatbot:latest .
```

### 2. Ejecutar los tests en el contenedor

Es obligatorio pasar `OPENAI_API_KEY` (para tests podés usar un valor ficticio):

```bash
docker run --rm -e OPENAI_API_KEY=sk-fake faq-rag-chatbot:latest
```

Por defecto el contenedor ejecuta pytest. Para otro comando, sobreescribilo al final:  
`docker run --rm -e OPENAI_API_KEY=sk-fake faq-rag-chatbot:latest python -m pytest tests/ -v`

### 3. Construir el índice (con tu API key y persistir ChromaDB)

Para `build_index` y `query` necesitás una **API key real** de OpenAI (no el valor ficticio de los tests). La forma más práctica es cargar las variables desde tu `.env` y usarlas en el contenedor:

```bash
export $(grep -v '^#' .env | xargs)
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY -v $(pwd)/chroma_db:/app/chroma_db faq-rag-chatbot:latest python -m src.build_index
```

Para forzar reconstrucción del índice: añadí `--force` al final del comando anterior.

Alternativa: si no usás `.env`, reemplazá `$OPENAI_API_KEY` por tu clave real (el texto `tu-key-real` en los ejemplos del README es solo un placeholder y fallará con error 401).

### 4. Hacer una consulta (misma API key y volumen)

Con las variables ya exportadas desde `.env` (mismo `export` del paso 3):

```bash
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY -v $(pwd)/chroma_db:/app/chroma_db faq-rag-chatbot:latest python -m src.query --question "¿Qué pasos debo seguir en mi proceso de onboarding?"
```

**Resumen:** siempre `-e OPENAI_API_KEY=...`; para `build_index` y `query` usá `-v $(pwd)/chroma_db:/app/chroma_db` para persistir el índice. Si al escribir en `chroma_db` ves errores de permisos (el contenedor corre como usuario no-root), podés usar `--user root` en ese `docker run` o asegurar que el directorio en el host sea escribible.

---

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

**Antes de hacer push:** podés validar en local (venv + pytest) o con Docker. Ver [docs/CI.md](docs/CI.md) sección **"Antes de push: validar en local"** y en este README **Probar localmente** / **Probar con Docker**.

**Si el workflow falla** (p. ej. "Process completed with exit code 2"): ver [docs/CI.md](docs/CI.md) para códigos de salida de pytest, cómo ver el log completo del paso "Run tests" y los ajustes aplicados en este repo.

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
- `Dockerfile` y `.dockerignore`: imagen Docker para ejecutar tests, `build_index` y `query` (ver sección **Probar con Docker** en este README).
- `docs/`: documentación (flujo de datos, decisiones RAG, prompts, checklist, **CI.md** para troubleshooting de GitHub Actions).
