#!/usr/bin/env bash
# Simula localmente el step "Debug imports" del workflow de CI.
# Requiere Python 3.11 (según PLAN y docs). Uso desde la raíz del repo:
#   python3.11 -m venv .venv-ci && source .venv-ci/bin/activate
#   pip install -r requirements.txt -r requirements-dev.txt && pip install -e .
#   ./scripts/simulate_ci_debug.sh

set -e
# Exigir Python 3.11+ (alineado con pyproject.toml y docs)
python -c "
import sys
v = sys.version_info
if v.major != 3 or v.minor < 11:
    print('Este proyecto requiere Python 3.11+. Actual:', sys.version, file=sys.stderr)
    sys.exit(1)
"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-fake-key-for-ci}"
export OPENAI_MODEL_ANSWER="${OPENAI_MODEL_ANSWER:-gpt-4o-mini}"
export OPENAI_MODEL_EVAL="${OPENAI_MODEL_EVAL:-gpt-4o-mini}"
export OPENAI_EMBEDDING_MODEL="${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}"
export PYTHONPATH="${PYTHONPATH:-.}"

echo "=== Python ==="
python -c "import sys; print(sys.version)"
echo "=== Checking chromadb ==="
python -c "import chromadb; print('chromadb OK')"
echo "=== Checking src ==="
python -c "import src; print('src OK')"
echo "=== Checking src.constants ==="
python -c "import src.constants; print('src.constants OK')"
echo "=== Checking src.config (needs OPENAI_* env) ==="
python -c "import src.config; print('src.config OK')"
echo "=== Checking src.build_index ==="
python -c "import src.build_index; print('src.build_index OK')"
echo "=== Checking src.query ==="
python -c "import src.query; print('src.query OK')"
echo "=== All imports OK ==="
echo ""
echo "=== Run tests (pytest, mismo que CI: -vv -rA --tb=long) ==="
python -m pytest tests/ -vv -rA --tb=long
