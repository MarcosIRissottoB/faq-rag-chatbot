# Python 3.11 (alineado con CI y pyproject.toml)
FROM python:3.11-slim

# System deps para ChromaDB/SQLite en Linux (igual que en .github/workflows/test.yml)
RUN apt-get update -q && apt-get install -y -q --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias primero (mejor cache de capas)
COPY requirements.txt requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt \
    && pip install --no-cache-dir .

# Código del proyecto (src, tests, data para build_index por defecto)
COPY src/ src/
COPY tests/ tests/
COPY data/ data/
COPY pytest.ini ./

# Usuario no-root (buena práctica para producción)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Variables por defecto para tests (OPENAI_API_KEY se pasa en runtime: -e OPENAI_API_KEY=sk-fake)
ENV OPENAI_MODEL_ANSWER=gpt-4o-mini
ENV OPENAI_MODEL_EVAL=gpt-4o-mini
ENV OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Por defecto ejecutar tests. Ejemplo: docker run --rm -e OPENAI_API_KEY=sk-fake faq-rag-chatbot:latest
CMD ["python", "-m", "pytest", "tests/", "-vv", "-rA", "--tb=long"]
