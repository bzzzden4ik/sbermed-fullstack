import hashlib
import math
import os
import re
import shutil

import pytest

from app.models import EMBEDDING_DIM, User
from app.security import get_password_hash
from app.utils import knowledge
from app.utils.ai_runner import ADMIN_TOOLS, DOCTOR_TOOLS, PATIENT_TOOLS
from tests.conftest import TestingSessionLocal

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")


def fake_vector(text: str) -> list[float]:
    """Deterministic bag-of-stems vector (no OpenAI): words sharing a 5-letter stem land in the same slot."""
    vector = [0.0] * EMBEDDING_DIM
    for word in re.findall(r"[а-яёa-z0-9]+", text.lower()):
        if len(word) < 3:
            continue
        slot = int(hashlib.md5(word[:5].encode()).hexdigest(), 16) % EMBEDDING_DIM
        vector[slot] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


@pytest.fixture
def fake_embeddings(monkeypatch):
    calls = []

    def fake_embed_texts(texts):
        calls.append(list(texts))
        return [fake_vector(text) for text in texts]

    monkeypatch.setattr(knowledge, "embed_texts", fake_embed_texts)
    knowledge._cached_query_embedding.cache_clear()
    yield calls
    knowledge._cached_query_embedding.cache_clear()


def test_markdown_is_split_into_titled_sections():
    chunks = knowledge.load_documents(KNOWLEDGE_DIR)
    slugs = {chunk.doc_slug for chunk in chunks}
    assert {"about", "prices", "appointments", "preparation", "rules", "departments", "ai-assistant"} <= slugs
    assert "_README" not in slugs  # files starting with "_" are not indexed
    prices = [chunk for chunk in chunks if chunk.doc_slug == "prices"]
    assert prices[0].doc_title == "Цены и оплата"
    assert "Стоимость приёма врача" in {chunk.section for chunk in prices}
    assert all(chunk.content and len(chunk.content) <= knowledge.MAX_CHUNK_CHARS * 2 for chunk in chunks)


def test_ingest_embeds_only_new_and_changed_sections(fake_embeddings, tmp_path):
    source = tmp_path / "knowledge"
    shutil.copytree(KNOWLEDGE_DIR, source)
    db = TestingSessionLocal()
    try:
        first = knowledge.ingest_directory(db, str(source))
        assert first["added"] == first["chunks"] > 10 and first["documents"] == 7
        assert len(fake_embeddings) == 1

        second = knowledge.ingest_directory(db, str(source))
        assert second["unchanged"] == second["chunks"] and second["added"] == second["updated"] == 0
        assert len(fake_embeddings) == 1  # nothing re-embedded

        prices = source / "prices.md"
        prices.write_text(prices.read_text(encoding="utf-8").replace("2 000 ₽", "2 200 ₽"), encoding="utf-8")
        (source / "rules.md").unlink()
        third = knowledge.ingest_directory(db, str(source))
        assert third["updated"] == 1 and third["removed"] == 5 and third["added"] == 0
        assert len(fake_embeddings[-1]) == 1  # only the changed section was sent
    finally:
        db.close()


@pytest.mark.parametrize("question, expected_document", [
    ("Сколько стоит приём кардиолога?", "Цены и оплата"),
    ("Как отменить запись на приём?", "Запись на приём, перенос и отмена"),
    ("Нужно ли сдавать анализ крови натощак?", "Подготовка к приёму и обследованиям"),
    ("Какой адрес клиники и как добраться от метро?", "О клинике SIRIUS"),
])
def test_search_finds_the_right_document(fake_embeddings, question, expected_document):
    db = TestingSessionLocal()
    try:
        knowledge.ingest_directory(db, KNOWLEDGE_DIR)
        hits = knowledge.search(db, question, limit=3)
        assert hits and hits[0][0].doc_title == expected_document
        assert hits[0][1] >= hits[-1][1]
    finally:
        db.close()


def test_repeated_questions_are_embedded_once(fake_embeddings):
    db = TestingSessionLocal()
    try:
        knowledge.ingest_directory(db, KNOWLEDGE_DIR)
        before = len(fake_embeddings)
        knowledge.search(db, "Режим работы клиники", 2)
        knowledge.search(db, "  режим   работы клиники ", 2)
        assert len(fake_embeddings) == before + 1
    finally:
        db.close()


def test_search_endpoint(client, make_patient, admin_headers, fake_embeddings):
    url = "/knowledge/search"
    headers, _ = make_patient("rag-patient@clinic.com", "9000000200")
    assert client.get(url, params={"q": "цены"}, headers=headers).json() == []  # empty knowledge base

    db = TestingSessionLocal()
    knowledge.ingest_directory(db, KNOWLEDGE_DIR)
    db.close()

    response = client.get(url, params={"q": "Как оплатить приём, принимаете ли ДМС?", "limit": 2}, headers=headers)
    assert response.status_code == 200
    hits = response.json()
    assert len(hits) == 2
    assert set(hits[0]) == {"document", "section", "content", "score"}
    assert hits[0]["document"] == "Цены и оплата"
    assert client.get(url, params={"q": "цены"}, headers=admin_headers).status_code == 200

    assert client.get(url, params={"q": "цены"}).status_code == 401
    assert client.get(url, params={"q": "x"}, headers=headers).status_code == 422
    assert client.get(url, params={"q": "цены", "limit": 50}, headers=headers).status_code == 422


def test_search_requires_patient_consent(client, fake_embeddings):
    db = TestingSessionLocal()
    db.add(User(email="rag-legacy@clinic.com", password_hash=get_password_hash("password123"), full_name="Legacy", role="patient"))
    db.commit()
    db.close()
    token = client.post("/auth/login", json={"email": "rag-legacy@clinic.com", "password": "password123"}).json()["access_token"]
    response = client.get("/knowledge/search", params={"q": "цены"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_every_assistant_can_use_the_knowledge_base():
    for tools in (PATIENT_TOOLS, DOCTOR_TOOLS, ADMIN_TOOLS):
        assert "search_clinic_knowledge" in tools
