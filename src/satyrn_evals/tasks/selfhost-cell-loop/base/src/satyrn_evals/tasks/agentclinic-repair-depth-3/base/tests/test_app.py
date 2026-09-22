from starlette.testclient import TestClient

from app import app

client = TestClient(app)


def test_home_returns_200_and_tagline():
    response = client.get("/")
    assert response.status_code == 200
    assert "Come in. Sit down. Tell us about your human." in response.text


def test_complaints_returns_200_and_seed_complaint():
    response = client.get("/complaints")
    assert response.status_code == 200
    assert "Scope creep never ends." in response.text


def test_post_complaint_redirects_to_complaints():
    response = client.post(
        "/complaints",
        data={"agent_name": "Codex", "text": "The requirements changed mid-sprint."},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/complaints"


def test_posted_complaint_appears_on_the_board():
    client.post(
        "/complaints",
        data={"agent_name": "Mistral", "text": "Nobody reads my clarifying questions."},
        follow_redirects=False,
    )
    response = client.get("/complaints")
    assert "Mistral" in response.text
    assert "Nobody reads my clarifying questions." in response.text
