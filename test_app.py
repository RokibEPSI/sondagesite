import json

import pytest

import app as sondage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Fichier de données temporaire : les tests ne touchent pas à polls.json
    data_file = tmp_path / "polls.json"
    data_file.write_text(json.dumps([
        {"question": "Q active", "options": [{"text": "A", "votes": 0}, {"text": "B", "votes": 0}],
         "status": "active", "voters": ["cookie-secret"]},
        {"question": "Q en attente", "options": [{"text": "A", "votes": 0}], "status": "pending", "voters": []},
    ]), encoding="utf-8")
    monkeypatch.setattr(sondage, "DATA_FILE", str(data_file))
    monkeypatch.setattr(sondage, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(sondage, "ADMIN_PASSWORD", "mot-de-passe-test")
    sondage.app.config.update(TESTING=True)
    return sondage.app.test_client()


def login(client, password="mot-de-passe-test"):
    return client.post("/login", data={"username": "admin", "password": password})


def test_first_visit_shows_page_and_sets_cookie(client):
    response = client.get("/")
    assert response.status_code == 200
    assert len(response.data) > 0
    assert "user_id=" in response.headers.get("Set-Cookie", "")


def test_public_api_hides_voters(client):
    polls = client.get("/api/polls").get_json()
    assert polls and all("voters" not in poll for poll in polls)


@pytest.mark.parametrize("method, url", [
    ("get", "/api/polls/pending"),
    ("post", "/api/polls/validate/0"),
    ("post", "/api/polls/expire/0"),
    ("delete", "/api/polls/refuse/0"),
    ("post", "/api/admin/create"),
])
def test_admin_api_requires_login(client, method, url):
    response = getattr(client, method)(url, json={"question": "Q", "options": ["A"]})
    assert response.status_code == 401


def test_admin_api_works_after_login(client):
    login(client)
    assert client.get("/api/polls/pending").status_code == 200
    assert client.post("/api/polls/validate/0").status_code == 200


def test_wrong_password_is_rejected(client):
    login(client, password="mauvais")
    assert client.get("/api/polls/pending").status_code == 401


def test_vote_once_and_invalid_option(client):
    client.get("/")  # reçoit le cookie user_id
    assert client.post("/api/vote/0/9").status_code == 404
    assert client.post("/api/vote/0/0").status_code == 200
    assert client.post("/api/vote/0/0").status_code == 403
