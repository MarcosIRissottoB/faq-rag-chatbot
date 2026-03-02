"""Tests unitarios para src/build_index.py: load_and_chunk_document, generate_embeddings, save_to_chroma, index_already_loaded."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.build_index import (
    load_and_chunk_document,
    generate_embeddings,
    save_to_chroma,
    index_already_loaded,
    main,
)
from src.constants import COLLECTION_NAME


class TestLoadAndChunkDocument:
    """Tests para load_and_chunk_document."""

    def test_archivo_no_encontrado_levanta_file_not_found(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            load_and_chunk_document("/ruta/inexistente/archivo.txt")
        assert "Documento no encontrado" in str(exc_info.value)

    def test_documento_vacio_levanta_value_error(self, empty_doc_path):
        with pytest.raises(ValueError) as exc_info:
            load_and_chunk_document(empty_doc_path)
        assert "vacío" in str(exc_info.value).lower()

    def test_documento_valido_devuelve_al_menos_20_chunks(self, valid_doc_path):
        chunks = load_and_chunk_document(valid_doc_path)
        assert len(chunks) >= 20
        for c in chunks:
            words = len(c.split())
            assert 50 <= words * 1.3 <= 500, f"Chunk con ~{words * 1.3:.0f} tokens fuera de rango"

    def test_chunk_excede_500_tokens_levanta_value_error(self, huge_chunk_doc_path):
        # Con chunk_size=400 un chunk puede superar 500 tokens (400*1.3=520)
        with pytest.raises(ValueError) as exc_info:
            load_and_chunk_document(huge_chunk_doc_path, chunk_size=400, overlap=50)
        assert "500 tokens" in str(exc_info.value) or "excede" in str(exc_info.value).lower()

    def test_menos_de_20_chunks_validos_levanta_value_error(self, small_doc_path):
        # small_doc tiene 2000 palabras; con chunk_size=300, overlap=50 → step 250 → 8 chunks
        with pytest.raises(ValueError) as exc_info:
            load_and_chunk_document(small_doc_path)
        assert "20 chunks" in str(exc_info.value) or "al menos 20" in str(exc_info.value).lower()

    def test_encoding_utf8(self, valid_doc_path):
        # Suficientes palabras para ≥20 chunks (chunk_size=300, overlap=50 → step 250; ~5100 palabras)
        valid_doc_path.write_text("palabra café ñoño " * 1700, encoding="utf-8")
        chunks = load_and_chunk_document(valid_doc_path, chunk_size=300, overlap=50)
        assert len(chunks) >= 20
        assert any("café" in c or "ñoño" in c for c in chunks)


class TestGenerateEmbeddings:
    """Tests para generate_embeddings con mock del provider."""

    def test_retorna_lista_de_vectores_con_mock(self):
        fake_embedding = [0.1] * 1536
        with patch("src.build_index.get_embedding_provider") as m_get:
            m_provider = MagicMock()
            m_provider.embed.side_effect = lambda chunk: list(fake_embedding)
            m_get.return_value = m_provider
            chunks = ["chunk uno", "chunk dos"]
            result = generate_embeddings(chunks)
        assert len(result) == 2
        assert result[0] == result[1] == fake_embedding
        assert m_provider.embed.call_count == 2

    def test_error_del_provider_levanta_runtime_error(self):
        with patch("src.build_index.get_embedding_provider") as m_get:
            m_provider = MagicMock()
            m_provider.embed.side_effect = Exception("API error")
            m_get.return_value = m_provider
            with pytest.raises(RuntimeError) as exc_info:
                generate_embeddings(["un chunk"])
            assert "embedding" in str(exc_info.value).lower() or "Error" in str(exc_info.value)


class TestSaveToChroma:
    """Tests para save_to_chroma con mock del vector store."""

    def test_llama_add_con_ids_y_metadata(self):
        chunks = ["doc1", "doc2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        doc_hash = "abc123"
        mock_collection = MagicMock()
        mock_store = MagicMock()
        mock_store.get_or_create_collection.return_value = mock_collection

        with patch("src.build_index.get_vector_store", return_value=mock_store):
            save_to_chroma(chunks, embeddings, doc_hash)

        mock_store.delete_collection.assert_called_once_with(name=COLLECTION_NAME)
        mock_store.get_or_create_collection.assert_called_once()
        call_kw = mock_store.get_or_create_collection.call_args[1]
        assert call_kw["metadata"]["doc_source_hash"] == doc_hash
        mock_collection.add.assert_called_once()
        add_kw = mock_collection.add.call_args[1]
        assert add_kw["ids"] == ["chunk_0", "chunk_1"]
        assert add_kw["documents"] == chunks
        assert add_kw["embeddings"] == embeddings

    def test_error_al_guardar_levanta_runtime_error(self):
        with patch("src.build_index.get_vector_store") as m_get:
            m_get.return_value.get_or_create_collection.side_effect = Exception("Chroma error")
            with pytest.raises(RuntimeError) as exc_info:
                save_to_chroma(["a"], [[0.1]], "hash")
            assert "ChromaDB" in str(exc_info.value) or "guardar" in str(exc_info.value).lower()


class TestIndexAlreadyLoaded:
    """Tests para index_already_loaded."""

    def test_true_si_mismo_hash_y_mismo_num_chunks(self):
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_coll.count.return_value = 25
        mock_coll.metadata = {"doc_source_hash": "abc"}
        mock_client.get_collection.return_value = mock_coll
        assert index_already_loaded(mock_client, "abc", 25) is True

    def test_false_si_hash_distinto(self):
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_coll.count.return_value = 25
        mock_coll.metadata = {"doc_source_hash": "other"}
        mock_client.get_collection.return_value = mock_coll
        assert index_already_loaded(mock_client, "abc", 25) is False

    def test_false_si_num_chunks_distinto(self):
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_coll.count.return_value = 30
        mock_coll.metadata = {"doc_source_hash": "abc"}
        mock_client.get_collection.return_value = mock_coll
        assert index_already_loaded(mock_client, "abc", 25) is False

    def test_false_si_no_existe_coleccion(self):
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("not found")
        assert index_already_loaded(mock_client, "abc", 25) is False

    def test_false_si_metadata_none(self):
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_coll.count.return_value = 25
        mock_coll.metadata = None
        mock_client.get_collection.return_value = mock_coll
        assert index_already_loaded(mock_client, "abc", 25) is False


class TestMain:
    """Tests para main (orquestación) con mocks."""

    def test_main_archivo_no_encontrado_levanta(self):
        with pytest.raises(FileNotFoundError):
            main("/no/existe.txt")

    def test_main_construye_indice_con_mocks(self, valid_doc_path):
        with patch("src.build_index.get_embedding_provider") as m_emb:
            with patch("src.build_index.get_vector_store") as m_store:
                m_emb.return_value.embed.side_effect = lambda c: [0.1] * 1536
                mock_coll = MagicMock()
                mock_coll.count.return_value = 0
                mock_coll.metadata = {}
                m_store.return_value.get_collection.return_value = mock_coll
                m_store.return_value.get_or_create_collection.return_value = MagicMock()

                main(valid_doc_path, force=True)

                m_store.return_value.get_or_create_collection.assert_called()
                add_call = m_store.return_value.get_or_create_collection.return_value.add
                add_call.assert_called_once()
