from tests.helpers import add_message, create_channel, create_user, login


class StubSummarize:
    def __init__(self, summary="Resume IA"):
        self.summary = summary
        self.calls = []

    def execute(self, actor, channel_id):
        self.calls.append((actor.id, channel_id))
        return self.summary


def _install_stub(app, stub):
    app.extensions["use_cases"].summarize_channel_messages = stub


def test_summary_requires_login(client):
    response = client.post("/ai/channels/1/summary")
    assert response.status_code == 302


def test_summary_returns_json_for_member(app, client):
    teacher_id = create_user(app, role="TEACHER", email="teacher.ai@test.local")
    channel_id = create_channel(app, "Classe 6A", created_by=teacher_id)
    add_message(app, channel_id, teacher_id, "Bonjour")
    add_message(app, channel_id, teacher_id, "Reunion lundi")

    stub = StubSummarize("- Reunion lundi")
    _install_stub(app, stub)
    login(client, teacher_id)

    response = client.post(f"/ai/channels/{channel_id}/summary")

    assert response.status_code == 200
    assert response.get_json() == {"summary": "- Reunion lundi"}
    assert stub.calls == [(teacher_id, channel_id)]


def test_summary_rejects_non_member_with_403(app, client):
    member_id = create_user(app, role="TEACHER", email="member.ai@test.local")
    outsider_id = create_user(app, role="PARENT", email="outsider.ai@test.local")
    channel_id = create_channel(app, "Canal prive", created_by=member_id)

    login(client, outsider_id)

    response = client.post(f"/ai/channels/{channel_id}/summary")

    assert response.status_code == 403
    assert response.get_json()["error"]


def test_summary_unknown_channel_returns_404(app, client):
    user_id = create_user(app, role="PARENT", email="unknown.ai@test.local")

    login(client, user_id)

    response = client.post("/ai/channels/9999/summary")

    assert response.status_code == 404
    assert response.get_json()["error"]


class StubRephrase:
    def __init__(self, suggestion="Version diplomatique"):
        self.suggestion = suggestion
        self.calls = []

    def execute(self, content):
        self.calls.append(content)
        return self.suggestion


def _install_rephrase_stub(app, stub):
    app.extensions["use_cases"].rephrase_draft = stub


def test_rephrase_requires_login(client):
    response = client.post("/ai/rephrase", json={"content": "Coucou"})
    assert response.status_code == 302


def test_rephrase_returns_suggestion_for_logged_in_user(app, client):
    user_id = create_user(app, role="TEACHER", email="rephrase.ai@test.local")
    stub = StubRephrase("Bonjour, pourrions-nous en discuter ?")
    _install_rephrase_stub(app, stub)
    login(client, user_id)

    response = client.post(
        "/ai/rephrase", json={"content": "  Repondez vite  "}
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "suggestion": "Bonjour, pourrions-nous en discuter ?"
    }
    assert stub.calls == ["  Repondez vite  "]


def test_rephrase_empty_content_returns_400(app, client):
    user_id = create_user(app, role="PARENT", email="empty.ai@test.local")
    login(client, user_id)

    response = client.post("/ai/rephrase", json={"content": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"]


def test_rephrase_missing_payload_returns_400(app, client):
    user_id = create_user(app, role="PARENT", email="nopayload.ai@test.local")
    login(client, user_id)

    response = client.post("/ai/rephrase", json={})

    assert response.status_code == 400
    assert response.get_json()["error"]
