# CI (GitHub Actions) — Tests y troubleshooting

Este documento describe el flujo de CI del proyecto y cómo diagnosticar fallos cuando el workflow **Tests** devuelve error en GitHub Actions.

---

## Qué hace el workflow

- **Archivo:** `.github/workflows/test.yml`
- **Disparadores:** push y pull request a las ramas `main` y `master`.
- **Pasos:**
  1. Checkout del código.
  2. Configuración de Python 3.11.
  3. **Show environment:** imprime versión de Python, `which python` y `pip list` (primeras 30 líneas) dentro de un grupo colapsable en el log de GH, para tener más detalle si algo falla.
  4. **Install system deps:** `build-essential` y `libsqlite3-dev` (ChromaDB/SQLite en Linux).
  5. Cache de pip (clave: hash de `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`).
  6. Instalación de dependencias: `pip install -r requirements.txt` y `pip install -r requirements-dev.txt`.
  7. **Install project:** `pip install -e .` (instalación editable desde `pyproject.toml` para resolver imports de `src`).
  8. **Debug imports:** ejecuta con `set -e` y un `echo` antes de cada comprobación (`=== Checking chromadb ===`, etc.) para que el log muestre **qué** se estaba comprobando cuando falló. Comprueba en orden: Python, chromadb, src, src.constants, src.config (requiere env OPENAI_*), src.build_index, src.query.
  9. **Run tests:** ejecuta `python -m pytest tests/ -vv -rA --tb=long` (verbose doble, resumen de todos los tests, traceback largo) con variables de entorno para CI.

El proyecto **sí tiene tests** en la carpeta `tests/`:

- `tests/conftest.py` — fixtures compartidos.
- `tests/test_build_index.py` — tests de `src.build_index`.
- `tests/test_query.py` — tests de `src.query`.

No es correcto afirmar que “el repo no tiene tests”; los tests existen y se ejecutan en CI.

---

## Códigos de salida de pytest

| Código | Significado |
|--------|-------------|
| 0 | Todos los tests pasaron. |
| 1 | Se ejecutaron tests y alguno falló. |
| 2 | Ejecución interrumpida (p. ej. error durante la colección de tests o interrupción). |
| 3 | Error interno de pytest. |
| 4 | Error de uso en la línea de comandos. |
| 5 | No se recolectó ningún test. |

Si el job **test (3.11)** falla con **exit code 2**, suele deberse a:

- Error de **import** al cargar `src` o sus dependencias (p. ej. no encontrar el paquete `src`).
- Error durante la **colección** de tests (módulo roto o dependencia faltante).
- En algunos entornos, fallos que pytest reporta como “interrumpido” (código 2).

---

## Cómo ver el error real en GitHub Actions

La anotación solo muestra algo como:

```text
Run tests
Process completed with exit code 2.
```

Para ver la causa:

1. Entra al **run** fallido en la pestaña **Actions**.
2. Haz clic en el **job** `test (3.11)`.
3. En la página del job, **haz clic en el paso "Run tests"** para expandirlo y ver el log completo del comando.
4. Desplázate al **final del log** de ese paso; ahí suele aparecer el traceback o el mensaje de error (por ejemplo `ModuleNotFoundError`, `ImportError`, `FAILED ...`).
5. Si en la lista de pasos no se expande nada, busca en la misma página un **bloque de log** (área de texto con la salida de todos los pasos) y usa **Ctrl+F / Cmd+F** para buscar: `Error`, `FAILED`, `ModuleNotFoundError`, `ImportError`, `pytest`.

El workflow está configurado con `--tb=long` para que, en caso de fallo, el traceback completo aparezca en ese log.

---

## Ajustes aplicados en este repo para evitar exit code 2

Se aplicaron estos cambios para que los tests pasen en CI:

1. **`PYTHONPATH: "."`** en el step **Run tests** del workflow.
2. **`src/__init__.py`** (archivo vacío) para que `src` sea un paquete Python.
3. **`python -m pytest ... --tb=long`** para tracebacks completos.
4. **Install system deps:** paso que instala `build-essential` y `libsqlite3-dev` en el runner Ubuntu. En Linux, ChromaDB suele necesitar estas dependencias para compilar/usar SQLite; sin ellas es muy común un **ImportError** al importar `chromadb` y pytest devuelve exit code 2 antes de ejecutar tests.
5. **`pyproject.toml`** en la raíz y paso **Install project** con `pip install -e .`. Así el paquete `src` queda instalado y los imports se resuelven sin depender solo de `PYTHONPATH`.
6. **Debug imports:** paso previo a **Run tests** con `set -e` y mensajes `echo "=== Checking X ==="` antes de cada import, para que el log indique exactamente en qué comprobación se rompió. **Importante:** `src.config` se ejecuta a nivel de módulo y llama a `_required()` para OPENAI_API_KEY, OPENAI_MODEL_ANSWER, OPENAI_MODEL_EVAL y OPENAI_EMBEDDING_MODEL; si alguna no está definida en el `env` del step, el import de `src.query` (o de `src.build_index` vía llm_adapter que usa config) falla. En CI esas variables deben estar en el step "Debug imports" y "Run tests".

Si tras un push el workflow sigue fallando, revisa en qué paso falla (Debug imports vs Run tests) y el mensaje en el log. Comprueba también que existan:

- `requirements.txt`, `requirements-dev.txt` y `pyproject.toml` en la raíz.
- Carpeta `tests/` con los archivos de test.
- Carpeta `src/` con `__init__.py` y los módulos que importan los tests.

---

## Resumen

- El workflow ejecuta los tests con pytest en Python 3.11; el proyecto tiene tests en `tests/`.
- **Exit code 2** suele indicar problema de imports o de colección de tests; el mensaje concreto está en el **log del paso "Run tests"** en GitHub Actions.
- Los cambios (system deps, `pip install -e .`, Debug imports, `PYTHONPATH`, `--tb=long`) están pensados para que CI sea estable y los fallos sean fáciles de diagnosticar (si falla Debug imports, se ve el import concreto; si falla Run tests, el traceback es largo).

Para ejecutar tests en local o con Docker, ver el [README](../README.md): secciones **Probar localmente** y **Probar con Docker**. Para construir el índice y hacer consultas con API real desde Docker, el README describe el uso de `export` desde `.env` y `OPENAI_API_KEY` en los comandos `docker run`.

---

## Antes de push: validar en local

Para **evitar que el workflow falle en GitHub** sin haber probado antes, podés validar de dos formas: (1) **en local** con venv y el script que replica el CI (Debug imports + pytest), o (2) **con Docker** (build + `docker run ...` con pytest). Ver el [README](../README.md), secciones **Probar localmente** y **Probar con Docker**. Si todo pasa en local o en el contenedor, es muy probable que pase en GH (salvo diferencias de sistema en Linux).

**Requisito:** Python 3.11 (véase README y docs/PRODUCTION_ROADMAP).

**Pasos (desde la raíz del repo):**

```bash
# 1. Venv con Python 3.11 (igual que en CI)
python3.11 -m venv .venv-ci
source .venv-ci/bin/activate   # Windows: .venv-ci\Scripts\activate

# 2. Instalar como en CI (deps + proyecto editable)
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .

# 3. Mismo flujo que el job de GH: Debug imports + Run tests
./scripts/simulate_ci_debug.sh
```

- Si el script termina en **0**: imports y tests OK; puedes hacer push con más confianza.
- Si falla: verás en qué paso se corta (`=== Checking X ===` o un test fallido) y el traceback; corrígelo antes de push.

Si no tienes Python 3.11: `pyenv install 3.11` o descarga desde python.org. El `pyproject.toml` exige `requires-python = ">=3.11"`.

---

## Simular el CI en local (detalle)

El proyecto requiere **Python 3.11**. Para reproducir exactamente los pasos de **Debug imports** y **Run tests** como en GitHub Actions:

1. Usar **Python 3.11** para crear el venv (igual que en CI). Desde la raíz del proyecto:
   ```bash
   python3.11 -m venv .venv-ci
   source .venv-ci/bin/activate   # Windows: .venv-ci\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   pip install -e .
   ```
2. Ejecutar el script que replica el step Debug imports y pytest:
   ```bash
   ./scripts/simulate_ci_debug.sh
   ```
   El script usa por defecto las variables de entorno de CI si no están definidas.

Si algo falla, verás en qué `=== Checking X ===` se corta. En macOS/Windows no se instalan las system deps de Linux (`build-essential`, `libsqlite3-dev`); si en CI falla solo en Linux, en local puede pasar.

---

## Qué ya probamos (si sigue fallando)

Lista de cambios aplicados para intentar resolver el fallo de CI (exit code 2). Si el workflow sigue fallando, sirve para no repetir y para probar alternativas.

| # | Qué probamos | Dónde | Resultado |
|---|----------------|-------|-----------|
| 1 | **PYTHONPATH: "."** en el step "Run tests" | `.github/workflows/test.yml` | Solo no alcanzaba |
| 2 | **src/__init__.py** (archivo vacío) | `src/__init__.py` | Solo no alcanzaba |
| 3 | **python -m pytest** en lugar de `pytest` | workflow | Aplicado |
| 4 | **--tb=long** para traceback completo | workflow | Aplicado |
| 5 | **Install system deps** (build-essential, libsqlite3-dev) | workflow, antes de Install dependencies | Aplicado — evita ImportError de chromadb en Linux |
| 6 | **pyproject.toml** + **pip install -e .** | `pyproject.toml` (nuevo) + step "Install project" | Aplicado — resuelve imports de `src` de forma robusta |
| 7 | **Debug imports** (chromadb, src, src.build_index, src.query) | workflow, antes de Run tests | Aplicado — diagnóstico: si falla, el log muestra qué import rompe |

---

## Alternativas a probar

Si el CI sigue con exit code 2, probar en este orden:

1. **Ver el log real:** En Actions → run fallido → job "test (3.11)" → expandir el paso **"Run tests"** y copiar el traceback/mensaje de error (ModuleNotFoundError, FAILED, etc.). Eso indica la causa exacta.
2. **Instalar el proyecto como paquete:** Crear `pyproject.toml` o `setup.py` y en el workflow añadir un step después de "Install dependencies": `pip install -e .` (instalación editable). Así `src` queda en el path sin depender de PYTHONPATH.
3. **Añadir paso de diagnóstico:** Antes de "Run tests", un step que ejecute `python -c "import sys; print(sys.path); import src; print('src OK')"` para comprobar en el log si `src` se importa.
4. **Desactivar cache de pip:** Comentar o quitar el step "Cache pip" por si la cache devuelve un entorno corrupto o desactualizado.
5. **Dependencias de sistema (ChromaDB):** Si el log muestra error al importar `chromadb` o al compilar, añadir antes de "Install dependencies" un step que instale dependencias del sistema, p. ej. `sudo apt-get update && sudo apt-get install -y build-essential`.
6. **Versiones de dependencias:** Revisar que `requirements.txt` y `requirements-dev.txt` tengan versiones compatibles con Python 3.11 en Linux; ChromaDB a veces requiere versiones concretas de numpy.
7. **Ejecutar tests por archivo:** En el workflow, cambiar a `python -m pytest tests/test_build_index.py -v --tb=long` (solo un archivo) para ver si el fallo es de colección o de un test concreto.
8. **Job mínimo de diagnóstico:** Crear un workflow aparte (p. ej. `ci-debug.yml`) que solo haga checkout, setup Python, pip install, y luego `python -c "import sys; sys.path.insert(0, '.'); import src.build_index; print('OK')"` para aislar si el problema es import o pytest.
