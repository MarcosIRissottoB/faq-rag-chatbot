# Roadmap de producción — FAQ RAG Chatbot

Análisis como **AI Engineer / Arquitecto** del repositorio `faq-rag-chatbot`: elementos **críticos** e **intermedios** para llevar el sistema a un nivel de producción (HR SaaS).

Cada ítem incluye: **motivo**, **explicación** y **sugerencia de mejora**.

---

## Resumen del estado actual

- **Stack:** Python 3.11, ChromaDB, OpenAI (embeddings + GPT-4o-mini), CLI (`build_index`, `query`).
- **Fortalezas:** Tests unitarios (pytest), CI (GitHub Actions; configuración y troubleshooting en [docs/CI.md](CI.md)), pre-commit (ruff, black, mypy), logging y timeout en llamadas LLM, configuración por `.env`, adaptadores para LLM y vector store.
- **Gaps principales:** Sin API HTTP, sin autenticación/autorización, sin observabilidad (métricas/trazas), configuración y secretos no listos para entornos múltiples, y dependencias/versiones desalineadas con el plan.

---

## Críticos (bloquean o comprometen producción)

### 1. API HTTP para consultas

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Hoy el sistema solo se usa por CLI (`python -m src.query --question "..."`). En producción, frontends (web/móvil), integraciones (Slack, Teams) o otros servicios necesitan un contrato HTTP estable (REST o similar). |
| **Explicación** | Sin API, no hay forma estándar de integrar el chatbot en un producto SaaS (login de usuario, rate limiting por tenant, CORS, etc.). El CLI es adecuado para scripts y operaciones internas, no para usuarios finales. |
| **Sugerencia** | Añadir una capa API mínima (por ejemplo **FastAPI**): `POST /v1/query` con body `{"question": "..."}` y respuesta JSON con la misma estructura que devuelve `main(question)`. Opcional: `GET /health` y `GET /ready` (ver punto 2). Mantener el CLI como wrapper que llame a la misma lógica de `src.query.main()`. Documentar OpenAPI (Swagger) y versionado (`/v1/`). |

---

### 2. Health checks y readiness

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Orquestadores (Kubernetes, ECS, etc.) y balanceadores necesitan saber si el proceso está vivo (liveness) y si puede atender tráfico (readiness). Sin esto, los reinicios y el despliegue son ciegos. |
| **Explicación** | Si la API no expone `/health` (y opcionalmente `/ready`), el platform team no puede configurar probes correctamente. Un fallo en ChromaDB o en la carga del índice debería reflejarse en readiness, no solo en el primer request. |
| **Sugerencia** | Implementar `GET /health`: responde 200 si el proceso está en marcha. `GET /ready`: comprueba que ChromaDB está accesible y la colección existe (e.g. `load_chroma_collection()` sin error); si falla, 503. Incluir en el mismo servicio que la API de consultas (punto 1). |

---

### 3. Gestión de secretos y configuración por entorno

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Hoy la API key y modelos se leen de `.env` con `python-dotenv`. En producción suele haber varios entornos (staging, prod) y los secretos no deben vivir en archivos versionados ni en variables de entorno en texto plano en el host. |
| **Explicación** | Si se despliega en cloud, lo habitual es usar un vault (AWS Secrets Manager, HashiCorp Vault, etc.) o variables inyectadas por el orquestador. Cargar todo desde un único `.env` local no escala y dificulta rotación de claves y auditoría. |
| **Sugerencia** | Introducir una capa de configuración que permita múltiples fuentes: (1) `.env` para desarrollo local, (2) variables de entorno (prioridad en producción), (3) opcionalmente un cliente de secret manager que sobrescriba solo las claves sensibles. No loguear nunca `OPENAI_API_KEY`. Documentar en README qué variables son obligatorias por entorno y ejemplos para CI/staging/prod. |

---

### 4. Límite de entrada (longitud y sanitización de la pregunta)

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Una pregunta sin límite puede provocar coste excesivo (embedding + LLM), timeouts o abusos. Además, hay que evitar inyección de prompts que alteren el comportamiento del sistema. |
| **Explicación** | En `query.py` solo se valida `len(question) >= 5` y que no esté vacía. No hay tope superior ni saneamiento. En producción, un usuario o un integrador podría enviar textos enormes o caracteres especiales que degraden la calidad o la seguridad. |
| **Sugerencia** | Definir en `constants.py` (o config) `MAX_QUESTION_LENGTH` (ej. 500–1000 caracteres). En el endpoint y en `main(question)` rechazar con 400 si se supera. Opcional: normalizar espacios y truncar con mensaje claro. Para el prompt: construir el `user_content` de forma que la pregunta del usuario esté claramente delimitada (ya se hace con "Pregunta del usuario: ...") y evitar incluir input crudo en el system prompt; si en el futuro se añade contenido controlado por el usuario en el system prompt, considerar un esquema de “sandbox” o instrucciones anti-inyección. |

---

### 5. Rate limiting y cuotas por cliente/tenant

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Cada consulta implica llamadas a OpenAI (embedding + respuesta + evaluación). Sin límites, un cliente o un bug pueden generar picos de coste y afectar al resto de usuarios. |
| **Explicación** | No existe actualmente ningún mecanismo de throttling ni de cuota por API key, usuario o tenant. En un HR SaaS típico se necesita al menos un límite por minuto/hora por identidad. |
| **Sugerencia** | Añadir rate limiting en la API (por IP, por API key o por `user_id`/`tenant_id` según el modelo de negocio). Opciones: middleware con `slowapi` (FastAPI), Redis para contadores distribuidos, o límites en API Gateway si se usa. Empezar con un límite global por instancia (ej. 60 req/min) y luego granular por tenant. Incluir headers `X-RateLimit-*` en la respuesta. |

---

### 6. Observabilidad: métricas y trazabilidad

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | En producción hay que saber cuántas consultas se hacen, latencias, errores y uso de modelos. Sin métricas no se puede dimensionar ni detectar regresiones (p. ej. degradación del RAG). |
| **Explicación** | Hoy solo hay logging a stdout (tiempos de LLM, errores). No hay métricas exportadas (Prometheus/StatsD) ni trazas distribuidas (OpenTelemetry). Tampoco hay correlación request → chunks → evaluación para analizar calidad. |
| **Sugerencia** | (1) **Métricas:** exponer `/metrics` en formato Prometheus (contador de requests, histogramas de latencia por paso: embedding, retrieval, answer, eval). (2) **Trazas:** instrumentar con OpenTelemetry (span por request y sub-spans por llamada a Chroma y OpenAI) y enviar a un backend (Jaeger, Grafana Tempo, vendor). (3) Opcional: log estructurado (JSON) con `request_id` y `trace_id` para correlacionar con métricas y trazas. No loguear preguntas/respuestas completas si hay PII; solo IDs y métricas agregadas. |

---

### 7. Dependencias y versiones (reproducibilidad y seguridad)

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | El `requirements.txt` actual no incluye `numpy` (ChromaDB lo usa); las versiones de `openai` y `chromadb` difieren de las del PLAN.md. Esto afecta reproducibilidad y posibles CVEs. |
| **Explicación** | En `requirements.txt` aparecen `openai==1.12.0`, `chromadb==0.4.24`; en PLAN.md se habla de `openai==1.54.3`, `chromadb==0.5.23`, `numpy==1.26.4`. La falta de `numpy` puede provocar fallos en CI o en distintos entornos. Versiones fijas y un lock file (e.g. `pip-tools`) reducen “works on my machine” y facilitan parches de seguridad. |
| **Sugerencia** | Alinear `requirements.txt` con las versiones que se usan realmente en desarrollo y CI; añadir `numpy` con versión acotada si ChromaDB lo requiere. Considerar `pip-compile` (pip-tools) para generar `requirements.txt` desde un `requirements.in` y fijar dependencias transitivas. Revisar periódicamente dependencias (e.g. `pip-audit`, Dependabot) y documentar en CONTRIBUTING o README el proceso de actualización. |

---

### 8. Persistencia del índice (ChromaDB) en entornos distribuidos

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | ChromaDB se usa en modo persistente en `./chroma_db`. En producción, con varias réplicas de la API o con reinicios frecuentes, el volumen debe ser compartido o el índice debe vivir en un servicio externo. |
| **Explicación** | Si cada pod monta su propio disco local, cada uno tendría que ejecutar `build_index` o tener una copia del índice; si el índice está en un volumen compartido, hay que garantizar que no se corrompa con escrituras concurrentes. ChromaDB en modo servidor (o un vector store gestionado) suele ser más adecuado para múltiples instancias. |
| **Sugerencia** | Para un solo nodo: documentar que `chroma_db` debe ser un volumen persistente y que solo un proceso debe escribir (jobs de `build_index`). Para múltiples nodos: evaluar ChromaDB en modo cliente-servidor o migrar a un vector store gestionado (Pinecone, Weaviate, etc.) usando el mismo adaptador `VectorStoreAdapter`; mantener la misma interfaz para no reescribir la lógica de negocio. |

---

## Intermedios (mejoran robustez y operación)

### 9. Timeout y reintentos en llamadas externas

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Ya existe timeout de 30 s en el adaptador LLM. Falta timeout explícito para ChromaDB y una política de reintentos ante fallos transitorios (red, throttling de OpenAI). |
| **Explicación** | Si ChromaDB o la red se colgan, la API puede quedar bloqueada. Si OpenAI devuelve 429, un retry con backoff mejora la experiencia sin tocar límites de forma agresiva. |
| **Sugerencia** | Configurar timeout en el cliente Chroma (si la API lo soporta) o en la capa HTTP subyacente. Para OpenAI: reintentos con backoff exponencial (ej. 2–3 intentos, solo para códigos 429/5xx), y opcionalmente circuit breaker si el fallo es sostenido. Parametrizar timeouts y número de reintentos por configuración. |

---

### 10. Evaluación de respuesta opcional o asíncrona

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Cada consulta incluye una llamada extra al LLM para `evaluate_response`, lo que duplica latencia y coste por request. En producción puede no ser necesario evaluar en línea para cada usuario. |
| **Explicación** | La evaluación es muy útil para calidad y para sample_queries; en tiempo real para cada pregunta puede ser demasiado costosa y lenta. |
| **Sugerencia** | Hacer la evaluación opcional: query param o header `X-Include-Evaluation: true/false` (por defecto `false` en producción). Alternativa: devolver la respuesta de inmediato y encolar la evaluación para un worker que rellene métricas o un log de calidad; el JSON de salida podría incluir `evaluation: null` cuando no se calcula. Mantener la posibilidad de activarla para cuentas premium o para muestreo (ej. 1% de tráfico). |

---

### 11. CORS y seguridad de cabeceras (si hay frontend web)

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Si la API es consumida por un frontend en otro origen, el navegador aplica CORS. Sin configuración, las peticiones pueden ser rechazadas. |
| **Explicación** | FastAPI permite configurar CORS por origen. Además, cabeceras como `X-Content-Type-Options`, `X-Frame-Options` y CSP reducen superficie de ataque. |
| **Sugerencia** | Configurar CORS en la API con una lista de orígenes permitidos (no `*` en producción). Añadir middleware de seguridad (cabeceras recomendadas) y documentar qué orígenes se aceptan en cada entorno. |

---

### 12. Índice: versionado y reindexación controlada

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Hoy el índice se invalida por hash del documento y `--force`. En producción, reindexar sobre el mismo path puede provocar ventanas donde la colección está vacía o a medias. |
| **Explicación** | `save_to_chroma` borra la colección y la recrea. Si dos procesos corren a la vez o si la API sirve durante el rebuild, pueden producirse errores o respuestas vacías. |
| **Sugerencia** | Estrategia “blue-green” para el índice: crear una colección con sufijo de versión o timestamp (ej. `faq_v2`), poblarla, y luego cambiar un puntero (metadata o config) para que la API use la nueva colección; después eliminar la antigua. Alternativa: job de reindexación en horario de bajo tráfico y un flag de mantenimiento que devuelva 503 en `/ready` hasta que termine. Documentar el proceso de actualización del FAQ en el runbook. |

---

### 13. Tests de integración y de contrato de la API

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Los tests actuales son unitarios con mocks. No se comprueba que el flujo completo (Chroma real o en memoria + OpenAI mockeado) ni el contrato HTTP funcionen. |
| **Explicación** | Un cambio en el formato de respuesta o en la ruta de la API podría romper integradores sin que los tests unitarios lo detecten. |
| **Sugerencia** | Añadir tests de integración: (1) con ChromaDB en memoria y mocks de OpenAI, ejecutar `build_index` + `query` y verificar estructura JSON. (2) Tests de API: con TestClient de FastAPI, `POST /v1/query` y comprobar status, schema JSON y que `chunks_related` y `evaluation` tengan el formato esperado. Opcional: contrato (Pact/OpenAPI) para consumidores. |

---

### 14. Documentación de operaciones y runbook

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Quien hace el deploy o el on-call necesita saber cómo levantar el servicio, cómo reindexar, qué variables son obligatorias y qué hacer ante fallos típicos. |
| **Estado actual** | El README documenta **Probar localmente** (tests, build_index, query con venv) y **Probar con Docker** (build, tests, build_index, query con `docker run` y variables/volúmenes). |
| **Sugerencia (cuando exista API)** | Añadir `docs/OPERATIONS.md` o ampliar README con: comando de arranque de la API, cómo ejecutar `build_index` en cron/job, dónde mirar logs y métricas, y un mini runbook (índice corrupto, OpenAI caído, alta latencia). |

---

### 15. Contenedorización (Docker)

| Aspecto | Detalle |
|--------|---------|
| **Motivo** | Facilita despliegues uniformes en cualquier entorno y evita “funciona en mi máquina” por diferencias de sistema o de Python. |
| **Estado actual** | El proyecto ya incluye `Dockerfile` y `.dockerignore`. La imagen permite ejecutar tests, `build_index` y `query`; los secretos se pasan en runtime (`-e OPENAI_API_KEY=...`). El [README](../README.md), sección **Probar con Docker**, describe cómo construir la imagen, ejecutar tests con clave ficticia y, para `build_index`/`query` con API real, cargar variables desde `.env` (`export $(grep -v '^#' .env | xargs)`) y usar `$OPENAI_API_KEY` en los `docker run`. |
| **Sugerencia (futuro)** | Cuando exista API HTTP: extender el Dockerfile o añadir etapa para servir la API (uvicorn). Opcional: `docker-compose.yml` con el servicio y un volumen para `chroma_db`. |

---

## Resumen de prioridades

| Prioridad | Ítem | Impacto |
|-----------|------|---------|
| **Crítico** | API HTTP + health/ready | Habilitar integración y despliegue |
| **Crítico** | Secretos y configuración por entorno | Seguridad y multi-entorno |
| **Crítico** | Límite y sanitización de pregunta | Coste, seguridad y estabilidad |
| **Crítico** | Rate limiting | Coste y fair use |
| **Crítico** | Observabilidad (métricas/trazas) | Operación y calidad |
| **Crítico** | Dependencias y versiones | Reproducibilidad y seguridad |
| **Crítico** | Persistencia del índice (multi-nodo) | Escalabilidad |
| **Intermedio** | Timeouts y reintentos | Resiliencia |
| **Intermedio** | Evaluación opcional/asíncrona | Coste y latencia |
| **Intermedio** | CORS y cabeceras de seguridad | Seguridad frontend |
| **Intermedio** | Versionado del índice | Zero-downtime reindexación |
| **Intermedio** | Tests de integración y API | Regresiones |
| **Intermedio** | Documentación de operaciones | Mantenibilidad |
| **Intermedio** | Docker | Despliegue y consistencia |

---

*Documento generado como análisis de arquitectura para producción. Implementar en el orden que mejor se adapte al equipo y al roadmap del producto.*
