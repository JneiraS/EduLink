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
