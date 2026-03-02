# Flujo de datos (resumen)

Resumen del flujo de datos del FAQ Chatbot RAG: desde la construcción del índice hasta la consulta y evaluación de respuestas.

---

## Diagrama

```mermaid
flowchart LR
  subgraph build [build_index]
    A[faq_document.txt] --> B[load_and_chunk]
    B --> C[generate_embeddings]
    C --> D[save_to_chroma]
  end
  subgraph query [query]
    E[question] --> F[load_chroma]
    F --> G[search_similar_chunks]
    G --> H[generate_answer]
    H --> I[evaluate_response]
    I --> J[JSON output]
  end
  D --> F
```

---

## Fases

| Fase | Descripción |
|------|-------------|
| **build_index** | Lee `data/faq_document.txt`, lo divide en chunks, genera embeddings con OpenAI y persiste todo en ChromaDB (colección `faq`). |
| **query** | Carga la colección ChromaDB, recibe una pregunta, busca chunks similares, genera la respuesta con el LLM y la evalúa; devuelve un JSON con pregunta, respuesta, chunks usados y evaluación. |

El enlace `D --> F` indica que la salida de ChromaDB (índice persistido) es la entrada del flujo de consulta al cargar la colección.

---

## Logging y resiliencia en el flujo de consulta

En el flujo de **query**, las llamadas al LLM están instrumentadas para no caer sin traza:

- **src/query.py:** logger por módulo; en `generate_answer` y `evaluate_response` se mide el tiempo de cada llamada al LLM y se registra con `logger.info`; ante fallo se usa `logger.error` antes de relanzar.
- **src/utils/llm_adapter.py:** en `OpenAILLMProvider.chat()` la llamada a la API tiene timeout de 30 s, medición de tiempo y logging de éxito/error, de modo que un fallo del LLM quede registrado y la excepción se propague de forma controlada.
