def test_audio_transcription_endpoint_returns_openai_transcript(client, monkeypatch, admin_headers):
    from app.config import settings
    from app.routes import ai

    captured = {}

    class FakeTranscriptions:
        async def create(self, *, model, file, response_format, language):
            captured["model"] = model
            captured["filename"] = file[0]
            captured["audio"] = file[1].read()
            captured["response_format"] = response_format
            captured["language"] = language
            return "Распознанный текст"

    class FakeClient:
        def __init__(self, *, api_key):
            assert api_key == "test-openai-key"
            self.audio = type("Audio", (), {"transcriptions": FakeTranscriptions()})()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(ai, "AsyncOpenAI", FakeClient)
    response = client.post(
        "/convert_audio_to_text",
        files={"file": ("sample.wav", b"audio data", "audio/wav")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Распознанный текст"}
    assert captured == {
        "model": "whisper-1",
        "filename": "sample.wav",
        "audio": b"audio data",
        "response_format": "text",
        "language": "ru",
    }


def test_audio_transcription_requires_api_key(client, monkeypatch, admin_headers):
    from app.config import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    response = client.post(
        "/convert_audio_to_text",
        files={"file": ("sample.wav", b"audio data", "audio/wav")},
        headers=admin_headers,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Audio transcription is not configured."


def test_audio_transcription_requires_authentication(client):
    response = client.post(
        "/convert_audio_to_text",
        files={"file": ("sample.wav", b"audio data", "audio/wav")},
    )

    assert response.status_code == 401

def test_conversation_lifecycle_is_authenticated_and_user_scoped(client, make_patient, fake_ai):
    headers, _ = make_patient("chat-patient@clinic.com", "9000000001")
    token = headers["Authorization"].removeprefix("Bearer ")

    create_response = client.post("/conversations", json={"message": "Первое сообщение"}, headers=headers)
    assert create_response.status_code == 201
    conversation = create_response.json()["conversation"]
    conversation_id = conversation["id"]
    assert [message["role"] for message in conversation["messages"]] == ["user", "assistant"]
    assert conversation["messages"][1]["content"] == "Ответ 1"
    assert conversation["case_status"] == "AI_COLLECTING"
    assert fake_ai[0]["user_token"] == token
    assert fake_ai[0]["context"] == [{"role": "user", "content": "Первое сообщение"}]
    assert f"conversation_id = {conversation_id}" in fake_ai[0]["instructions"]

    send_response = client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Продолжение"}, headers=headers
    )
    assert send_response.status_code == 201
    assert send_response.json()["assistant_message"]["content"] == "Ответ 2"
    assert [message["role"] for message in fake_ai[1]["context"]] == ["user", "assistant", "user"]

    list_response = client.get("/conversations", headers=headers)
    assert [item["id"] for item in list_response.json()] == [conversation_id]
    assert len(client.get(f"/conversations/{conversation_id}", headers=headers).json()["messages"]) == 4

    other_headers, _ = make_patient("another-patient@clinic.com", "9000000002")
    assert client.get(f"/conversations/{conversation_id}", headers=other_headers).status_code == 404
    assert client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Чужой"}, headers=other_headers
    ).status_code == 404

    # Deleting an unsent conversation also removes its draft case.
    assert client.delete(f"/conversations/{conversation_id}", headers=headers).status_code == 204
    assert client.get(f"/conversations/{conversation_id}", headers=headers).status_code == 404
    assert client.get("/cases", headers=headers).json() == []
    assert len(fake_ai) == 2


def test_failed_ai_reply_does_not_leave_duplicate_messages(client, make_patient, monkeypatch):
    from app.routes import ai

    async def failing_ai_runner(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(ai, "ai_runner", failing_ai_runner)
    headers, _ = make_patient("fail-patient@clinic.com", "9000000003")
    response = client.post("/conversations", json={"message": "Болит голова"}, headers=headers)
    assert response.status_code == 502
    assert client.get("/conversations", headers=headers).json() == []
    assert client.get("/cases", headers=headers).json() == []
