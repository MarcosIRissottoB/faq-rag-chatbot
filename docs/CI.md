# CI (GitHub Actions) — Tests y troubleshooting

Este documento describe el flujo de CI del proyecto y cómo diagnosticar fallos cuando el workflow **Tests** devuelve error en GitHub Actions.

---

## Qué hace el workflow

- **Archivo:** `.github/workflows/test.yml`
- **Disparadores:** push y pull request a las ramas `main` y `master`.
- **Pasos:**
  1. Checkout del código.
  2. Configuración de Python 3.11.
  3. Cache de pip (clave: hash de `requirements.txt` y `requirements-dev.txt`).
  4. Instalación de dependencias: `pip install -r requirements.txt` y `pip install -r requirements-dev.txt`.
  5. **Run tests:** ejecuta `python -m pytest tests/ -v --tb=long` con variables de entorno para CI (API key falsa, modelos, etc.).

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

1. **`PYTHONPATH: "."`** en el step **Run tests** del workflow, para que el intérprete encuentre el paquete `src` desde la raíz del repo.
2. **`src/__init__.py`** (archivo vacío) para que `src` sea un paquete Python y los imports `from src.build_index` / `from src.query` funcionen en el runner.
3. **`python -m pytest tests/ -v --tb=long`** para usar el mismo Python donde se instalaron las dependencias y para obtener tracebacks largos si algo falla.

Si tras un push el workflow sigue fallando, revisa el log del paso **Run tests** (como en la sección anterior) y comprueba que existan:

- `requirements.txt` y `requirements-dev.txt` en la raíz.
- Carpeta `tests/` con los archivos de test.
- Carpeta `src/` con `__init__.py` y los módulos que importan los tests.

---

## Resumen

- El workflow ejecuta los tests con pytest en Python 3.11; el proyecto tiene tests en `tests/`.
- **Exit code 2** suele indicar problema de imports o de colección de tests; el mensaje concreto está en el **log del paso "Run tests"** en GitHub Actions.
- Los cambios de `PYTHONPATH`, `src/__init__.py` y `python -m pytest ... --tb=long` están pensados para que CI sea estable y los fallos sean fáciles de diagnosticar.

Para más detalle sobre cómo ejecutar tests en local, ver la sección **Tests** del [README](../README.md).
