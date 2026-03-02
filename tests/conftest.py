"""Fixtures compartidos para tests. Documento temporal válido para chunking (≥20 chunks, 50–500 tokens por chunk)."""

import pytest


@pytest.fixture
def valid_doc_path(tmp_path):
    """Crea un archivo con ~5100 palabras para producir ≥20 chunks válidos (chunk_size=300, overlap=50)."""
    # 5100 palabras → ~22 chunks de 300 palabras (~390 tokens cada uno)
    words = ["palabra"] * 5100
    text = " ".join(words)
    path = tmp_path / "faq_document.txt"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def small_doc_path(tmp_path):
    """Documento con pocas palabras: genera menos de 20 chunks válidos (para test de validación)."""
    words = ["x"] * 2000  # pocos chunks, todos válidos en tamaño pero < 20
    path = tmp_path / "small.txt"
    path.write_text(" ".join(words), encoding="utf-8")
    return path


@pytest.fixture
def empty_doc_path(tmp_path):
    """Archivo vacío (para test FileNotFoundError/ValueError)."""
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def huge_chunk_doc_path(tmp_path):
    """Documento con un bloque de >385 palabras en una línea/segmento que forme un chunk >500 tokens."""
    # Un chunk de 400 palabras → 520 tokens → debe fallar validación.
    # Necesitamos 20+ chunks; el primero será enorme. Con step 250, chunk 0 tiene words[0:300].
    # Para forzar un chunk >500 tokens: 500/1.3 ≈ 385 palabras. Crear doc donde el primer chunk tenga 400 palabras.
    words = ["w"] * 400 + ["z"] * 5000  # primer chunk 400 palabras
    path = tmp_path / "huge.txt"
    path.write_text(" ".join(words), encoding="utf-8")
    return path
