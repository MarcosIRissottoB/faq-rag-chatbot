# Checklist de rúbrica

Checklist completo mapeado a cada indicador de la rúbrica. Para cada ítem se indica el archivo y la función o sección donde se cumple.

---

## Tabla de indicadores

| Indicador rúbrica | Archivo | Función/sección | Estado |
|-------------------|---------|-----------------|--------|
| ≥20 chunks distintos | src/build_index.py | load_and_chunk_document() | ✅ validado en código |
| Cada chunk 50-500 tokens | src/build_index.py | load_and_chunk_document() | ✅ validado en código |
| Estrategia documentada | docs/rag_decisions.md | Estrategia de chunking | ✅ |
| chunk_size y overlap como parámetros | src/build_index.py | load_and_chunk_document() | ✅ |
| Embeddings = cantidad de chunks | src/build_index.py | generate_embeddings() | ✅ |
| Modelo text-embedding-3-small | src/build_index.py | generate_embeddings() | ✅ |
| Embeddings guardados | src/build_index.py | save_to_chroma() | ✅ ChromaDB |
| JSON con 3 claves exactas | src/query.py | main() | ✅ user_question, system_answer, chunks_related, evaluation |
| Similitud coseno explícita | src/query.py | search_similar_chunks() | ✅ score de ChromaDB |
| Método de búsqueda documentado | docs/rag_decisions.md | Método de búsqueda | ✅ |
| 2-5 chunks por consulta | src/query.py | search_similar_chunks() | ✅ top_k validado |
| 4 etapas build pipeline | src/build_index.py | main() | ✅ load → embed → save |
| 4 etapas query pipeline | src/query.py | main() | ✅ load → search → generate → evaluate |
| RAG flujo 2 pasos visible | src/query.py | main() | ✅ recuperación antes de generación |
| RAG documentado con beneficios | docs/rag_decisions.md | Por qué RAG | ✅ |
| ≥4 funciones descriptivas | src/build_index.py + query.py | todas | ✅ |
| Funciones ≤30 líneas | src/build_index.py + query.py | todas | ✅ |
| README ≥50 palabras descripción | README.md | Descripción | ✅ |
| README 3+ pasos instalación | README.md | Instalación | ✅ |
| README ejemplo con JSON output | README.md | Uso | ✅ |
| README decisiones técnicas | README.md + docs/rag_decisions.md | Decisiones | ✅ |
| requirements.txt con versiones | requirements.txt | — | ✅ |
| API key con os.getenv | src/build_index.py + query.py | todas | ✅ |
| evaluate_response score 0-10 | src/query.py | evaluate_response() | ✅ |
| evaluate_response reason ≥50 chars | src/query.py | evaluate_response() | ✅ |
| Evalúa ≥2 dimensiones | src/query.py + docs/prompts.md | evaluate_response() | ✅ 3 dimensiones |
| reason con observaciones específicas | docs/prompts.md | Prompt evaluador | ✅ |

**Nota:** El JSON de salida tiene 4 claves (`user_question`, `system_answer`, `chunks_related`, `evaluation`); la rúbrica puede referirse a “3 claves” en sentido de bloques principales; en cualquier caso el formato exigido en el plan es el de la tabla (las 4 claves listadas).

---

## Cómo verificar antes de entregar

Comandos y comprobaciones para validar cada punto crítico.

### 1. Entorno y dependencias

```bash
# Versiones de paquetes en requirements.txt
cat requirements.txt
# Debe listar openai, chromadb, numpy, python-dotenv con versiones.

# API key cargada por entorno
grep -n "os.getenv.*OPENAI_API_KEY" src/build_index.py src/query.py
# Debe aparecer en los módulos que usan OpenAI.
```

### 2. Build del índice

```bash
# Crear índice desde el documento por defecto
python src/build_index.py

# Comprobar que imprime: nº chunks (≥20), dimensión de embedding, ruta de ChromaDB.
# Comprobar que existe el directorio de ChromaDB (ej. chroma_db/).
```

### 3. Chunking y validaciones

```bash
# En el código: load_and_chunk_document debe validar ≥20 chunks y 50–500 tokens por chunk.
# Si el documento es demasiado corto o los chunks salen del rango, debe fallar con mensaje claro.
grep -n "chunk_size\|overlap\|50\|500\|20" src/build_index.py
```

### 4. Query y formato de salida

```bash
# Una consulta de ejemplo
python src/query.py --question "¿Qué pasos debo seguir en mi proceso de onboarding?"

# La salida debe ser un único JSON con: user_question, system_answer, chunks_related (lista de {text, score}), evaluation (score, reason).
# chunks_related debe tener entre 2 y 5 elementos.
python src/query.py --question "¿Cuántos días de vacaciones tengo?" | python -m json.tool
```

### 5. Evaluación (score y reason)

```bash
# Tras una consulta, comprobar en el JSON:
# - evaluation.score es un entero entre 0 y 10.
# - evaluation.reason tiene al menos 50 caracteres.
# - El reason menciona relevancia de chunks, calidad de respuesta y completitud (ver docs/prompts.md).
```

### 6. Documentación

```bash
# Decisiones RAG
cat docs/rag_decisions.md

# Prompts exactos
cat docs/prompts.md

# README: descripción ≥50 palabras, instalación con 3+ pasos, ejemplo de uso con JSON
wc -w README.md
grep -A 20 "Instalación\|Installation\|Uso\|Usage" README.md
```

### 7. Estructura de código

```bash
# Funciones en build_index: load_and_chunk_document, generate_embeddings, save_to_chroma, main
grep -n "^def " src/build_index.py

# Funciones en query: load_chroma_collection, search_similar_chunks, generate_answer, evaluate_response, main
grep -n "^def " src/query.py

# Longitud de funciones (cada una ≤30 líneas; revisar manualmente si hace falta)
wc -l src/build_index.py src/query.py
```

### 8. Sample queries (respuestas reales)

```bash
# outputs/sample_queries.json debe existir y contener 3 entradas con el mismo formato que main(question).
# Cada entrada debe tener user_question, system_answer, chunks_related, evaluation.
cat outputs/sample_queries.json | python -m json.tool
```

Ejecutar estos pasos antes de la entrega asegura que el proyecto cumple los requisitos de la rúbrica documentados en este checklist.
