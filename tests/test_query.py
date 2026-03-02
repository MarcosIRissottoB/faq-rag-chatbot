"""Tests unitarios para src/query.py: load_chroma_collection, search_similar_chunks, generate_answer, evaluate_response, main."""

import pytest
from unittest.mock import patch, MagicMock

from src.query import (
    load_chroma_collection,
    search_similar_chunks,
    generate_answer,
    evaluate_response,
    main,
)


class TestLoadChromaCollection:
    """Tests para load_chroma_collection."""

    def test_devuelve_coleccion_cuando_existe(self):
        mock_coll = MagicMock()
        mock_store = MagicMock()
        mock_store.get_collection.return_value = mock_coll
        with patch("src.query.get_vector_store", return_value=mock_store):
            result = load_chroma_collection()
        assert result is mock_coll
        mock_store.get_collection.assert_called_once()

    def test_levanta_runtime_error_si_no_existe_coleccion(self):
        mock_store = MagicMock()
        mock_store.get_collection.side_effect = Exception("Collection not found")
        with patch("src.query.get_vector_store", return_value=mock_store):
            with pytest.raises(RuntimeError) as exc_info:
                load_chroma_collection()
        assert (
            "No se pudo cargar" in str(exc_info.value)
            or "colección" in str(exc_info.value).lower()
        )


class TestSearchSimilarChunks:
    """Tests para search_similar_chunks."""

    def test_retorna_lista_dict_text_score(self):
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "distances": [[0.1, 0.3]],
        }
        fake_embedding = [0.1] * 1536
        with patch("src.query.get_embedding_provider") as m_get:
            m_get.return_value.embed.return_value = fake_embedding
            result = search_similar_chunks("pregunta", mock_coll, top_k=3)
        assert len(result) == 2
        assert result[0]["text"] == "doc1" and "score" in result[0]
        assert result[1]["text"] == "doc2" and "score" in result[1]
        assert isinstance(result[0]["score"], (int, float))

    def test_restringe_top_k_entre_2_y_5(self):
        mock_coll = MagicMock()
        mock_coll.query.return_value = {"documents": [[]], "distances": [[]]}
        with patch("src.query.get_embedding_provider") as m_get:
            m_get.return_value.embed.return_value = [0.0] * 10
            search_similar_chunks("q", mock_coll, top_k=10)
            mock_coll.query.assert_called_once()
            assert mock_coll.query.call_args[1]["n_results"] == 5
            mock_coll.reset_mock()
            search_similar_chunks("q", mock_coll, top_k=1)
            assert mock_coll.query.call_args[1]["n_results"] == 2


class TestGenerateAnswer:
    """Tests para generate_answer."""

    def test_llama_llm_y_devuelve_texto(self):
        chunks = [{"text": "Contexto A"}, {"text": "Contexto B"}]
        with patch("src.query.get_llm_provider") as m_get:
            m_get.return_value.chat.return_value = "Respuesta generada."
            result = generate_answer("¿Pregunta?", chunks)
        assert result == "Respuesta generada."
        m_get.return_value.chat.assert_called_once()
        call_kw = m_get.return_value.chat.call_args[1]
        assert "Contexto A" in call_kw["user"]
        assert "Contexto B" in call_kw["user"]
        assert "¿Pregunta?" in call_kw["user"]

    def test_error_llm_levanta_runtime_error(self):
        with patch("src.query.get_llm_provider") as m_get:
            m_get.return_value.chat.side_effect = Exception("API error")
            with pytest.raises(RuntimeError) as exc_info:
                generate_answer("q", [{"text": "c"}])
            assert "generar" in str(exc_info.value).lower() or "Error" in str(
                exc_info.value
            )


class TestEvaluateResponse:
    """Tests para evaluate_response."""

    def test_retorna_score_y_reason_desde_json_llm(self):
        raw_json = '{"score": 8, "reason": "La respuesta es relevante y completa, citando correctamente el contexto proporcionado en los chunks."}'
        with patch("src.query.get_llm_provider") as m_get:
            m_get.return_value.chat.return_value = raw_json
            result = evaluate_response("p", "answer", [{"text": "chunk"}])
        assert result["score"] == 8
        assert len(result["reason"]) >= 50
        assert "relevante" in result["reason"] or "completa" in result["reason"]

    def test_reason_corto_se_completa_a_50_caracteres(self):
        with patch("src.query.get_llm_provider") as m_get:
            m_get.return_value.chat.return_value = '{"score": 5, "reason": "Ok"}'
            result = evaluate_response("p", "a", [{"text": "c"}])
        assert result["score"] == 5
        assert len(result["reason"]) >= 50

    def test_json_invalido_devuelve_score_0_y_reason_de_error(self):
        with patch("src.query.get_llm_provider") as m_get:
            m_get.return_value.chat.return_value = "No soy JSON"
            result = evaluate_response("p", "a", [{"text": "c"}])
        assert result["score"] == 0
        assert "reason" in result and len(result["reason"]) > 0


class TestMain:
    """Tests para main (orquestación)."""

    def test_retorna_estructura_json_obligatoria(self):
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "documents": [["chunk1", "chunk2"]],
            "distances": [[0.2, 0.4]],
        }
        with patch("src.query.load_chroma_collection", return_value=mock_coll):
            with patch("src.query.get_embedding_provider") as m_emb:
                m_emb.return_value.embed.return_value = [0.0] * 10
                with patch("src.query.get_llm_provider") as m_llm:
                    m_llm.return_value.chat.side_effect = [
                        "Respuesta RAG",
                        '{"score": 7, "reason": "Evaluación suficiente con al menos cincuenta caracteres de justificación."}',
                    ]
                    result = main("¿Pregunta de prueba?")
        assert "user_question" in result
        assert "system_answer" in result
        assert "chunks_related" in result
        assert "evaluation" in result
        assert result["user_question"] == "¿Pregunta de prueba?"
        assert result["system_answer"] == "Respuesta RAG"
        assert isinstance(result["chunks_related"], list)
        for c in result["chunks_related"]:
            assert "text" in c and "score" in c
        assert result["evaluation"]["score"] == 7
        assert "reason" in result["evaluation"]
