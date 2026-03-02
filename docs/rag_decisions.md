# Decisiones técnicas RAG

Documento que justifica explícitamente las decisiones de diseño del sistema RAG según la rúbrica de evaluación.

---

## Estrategia de chunking

### Método elegido

**Tamaño fijo con overlap:** `chunk_size=300` palabras, `overlap=50` palabras.

### Por qué este método y no por párrafos ni semántico

- **Por párrafos:** Los párrafos del FAQ pueden ser muy largos o muy cortos; no garantizan un rango de tokens uniforme (50–500). Además, una pregunta puede requerir información repartida en varios párrafos, y el tamaño variable complica el control de coste y de ventana de contexto.
- **Semántico:** Requeriría un modelo adicional para segmentar por “temas” o oraciones, añadiendo complejidad y dependencias. Para un corpus de FAQ acotado, la ventana fija con overlap es suficiente y reproducible.
- **Tamaño fijo con overlap:** Permite controlar exactamente el tamaño (300 palabras ≈ ~390 tokens con factor ~1,3), cumplir el rango 50–500 tokens, y el overlap de 50 palabras evita cortar frases en el límite y mantiene contexto entre chunks adyacentes.

### Por qué estos valores de chunk_size y overlap

- **chunk_size=300 palabras:** Equivale aproximadamente a 300 × 1,3 ≈ 390 tokens, dentro del rango 50–500. Chunks más pequeños fragmentarían demasiado; más grandes podrían mezclar temas y superar el límite superior.
- **overlap=50 palabras:** Suficiente para no partir una oración o una idea a la mitad en el borde del chunk; no tan grande como para duplicar contenido de forma excesiva ni aumentar innecesariamente el número de chunks.

### Cómo se garantiza el rango 50–500 tokens

En el código se valida tras generar los chunks:

- Estimar tokens por chunk (p. ej. `palabras × 1,3` o usando `tiktoken` si se incorpora).
- Comprobar que cada chunk esté entre 50 y 500 tokens (inclusive).
- Comprobar que el documento genere **≥20 chunks** distintos.
- Si no se cumple, se lanza un error claro (archivo, mensaje explícito) para corregir el documento o los parámetros.

### Parámetros en el código

- **Archivo:** `src/build_index.py` (y valores por defecto en `src/constants.py`).
- **Función:** `load_and_chunk_document(path, chunk_size=300, overlap=50)`.
- **Valores por defecto:** definidos en `src/constants.py` como `CHUNK_SIZE_DEFAULT` (300) y `CHUNK_OVERLAP_DEFAULT` (50); el script `build_index` los usa cuando no se pasan argumentos.
- **Override por CLI:** se pueden sobrescribir con `--chunk-size` y `--chunk-overlap` al ejecutar `python -m src.build_index`.
- La estrategia es configurable sin tocar la lógica interna (constantes o argumentos de función).

---

## Método de búsqueda vectorial

### Método elegido

**k-NN (k-Nearest Neighbors)** con **similitud coseno** vía ChromaDB.

### Por qué k-NN y no ANN, range query ni híbrido

- **ANN (Approximate Nearest Neighbors):** Pensado para escalar a millones de vectores; para un índice de decenas de chunks (FAQ), el k-NN exacto es suficiente y más simple, sin sacrificar precisión.
- **Range query:** Fija un umbral de similitud; el número de resultados es variable (0, 1, muchos). La rúbrica pide un número controlado de chunks por consulta (2–5); k-NN con `top_k` fijo cumple esto de forma directa.
- **Híbrido (vectorial + léxico):** Añade complejidad y más dependencias; para un único documento FAQ en español, la búsqueda solo por embeddings es adecuada.
- **k-NN:** Recupera siempre los `top_k` chunks más similares al vector de la pregunta; comportamiento determinista y fácil de documentar y evaluar.

### Por qué similitud coseno y no producto punto ni euclidiana

- **Producto punto:** Depende de la norma de los vectores; con embeddings normalizados coincide con coseno, pero la rúbrica pide que el método de similitud esté justificado; coseno es el estándar en ChromaDB para embeddings y está bien documentado.
- **Distancia euclidiana:** Penaliza la magnitud del vector; los embeddings de OpenAI suelen usarse con coseno, y ChromaDB lo soporta de forma nativa.
- **Coseno:** Mide el ángulo entre vectores (independiente de la norma); adecuado para comparar embeddings de texto y es el que ChromaDB usa por defecto en la colección (y se expone como score en los resultados).

### Por qué top_k=5 como valor por defecto

- Rango válido en la rúbrica: **2–5** chunks por consulta.
- **top_k=5** mejora el recall en preguntas cortas (p. ej. "¿Cuántos días de vacaciones tengo?") y asegura que entren más fragmentos relevantes antes de generar la respuesta. El parámetro `top_k` se valida en código para que esté siempre en [2, 5].

### Dónde se calcula explícitamente la similitud

- **Archivo:** `src/query.py`
- **Función:** `search_similar_chunks(question, collection, top_k=5)` `query_embeddings` y `n_results=top_k`. ChromaDB utiliza similitud coseno internamente y devuelve cada resultado con un **score** (similitud). El código retorna una lista de diccionarios con `"text"` y `"score"`; ese `score` es la similitud coseno calculada por ChromaDB para cada chunk recuperado.

---

## Por qué RAG y no fine-tuning

### Beneficios de RAG en este contexto

- **Conocimiento actualizable:** El FAQ puede cambiarse editando `data/faq_document.txt` y re-ejecutando `build_index.py`, sin reentrenar ningún modelo.
- **Transparencia:** Cada respuesta se basa en chunks recuperados que se devuelven en `chunks_related`; el usuario puede ver exactamente qué fragmentos se usaron.
- **Atribución de fuentes:** Los chunks son trazables al documento fuente; la evaluación puede comprobar que la respuesta se apoya en esos fragmentos y no en información inventada.

### Cómo se implementa el flujo en 2 pasos (recuperación ANTES de generación)

1. **Paso 1 – Recuperación:** Dada la pregunta del usuario, se buscan los `top_k` chunks más similares (k-NN con coseno en ChromaDB). No se genera texto aún.
2. **Paso 2 – Generación:** Con la pregunta y solo esos chunks como contexto, se llama al LLM (`generate_answer`) para producir la respuesta.

Este orden está implementado en `src/query.py` en `main(question)`:

1. `load_chroma_collection()`
2. `search_similar_chunks(question, collection, top_k)` → se obtienen los chunks y sus scores
3. `generate_answer(question, chunks)` → se inyectan esos chunks en el prompt y se genera la respuesta
4. `evaluate_response(question, answer, chunks)` → se evalúa la respuesta con los mismos chunks

La recuperación siempre ocurre antes de la generación; no se usa el LLM para “elegir” chunks, solo para responder a partir de los ya recuperados.

---

## Operación y resiliencia en llamadas al LLM

Para que un fallo del LLM no derribe la aplicación sin traza y se puedan observar tiempos de respuesta:

- **Adaptador (src/utils/llm_adapter.py):** En `OpenAILLMProvider.chat()` se configura un logger a nivel de módulo; la llamada a `client.chat.completions.create` se hace con `timeout=30`, dentro de un `try` que mide el tiempo y registra éxito con `logger.info`; en el `except` se registra el error con `logger.error` y se relanza la excepción.
- **Orquestador (src/query.py):** En `generate_answer` y `evaluate_response` se mide el tiempo alrededor de `get_llm_provider().chat(...)`, se registra la duración con `logger.info` y, en caso de excepción, se usa `logger.error` antes de relanzar `RuntimeError`.

Así las fallas de red o de API quedan registradas y el comportamiento es predecible (timeout y re-raise) en lugar de caídas silenciosas.
