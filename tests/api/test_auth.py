from tests.api.conftest import register_and_login

NEW_USER = {"username": "carol", "email": "carol@example.com", "password": "secret123"}


def test_register_returns_the_user_without_the_password(client):
    response = client.post("/auth/register", json=NEW_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "carol" and body["email"] == "carol@example.com"
    assert "password" not in body and "hashed_password" not in body


def test_duplicate_account_is_rejected(client):
    client.post("/auth/register", json=NEW_USER)
    response = client.post("/auth/register", json=NEW_USER)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_validates_input(client):
    assert client.post("/auth/register", json={**NEW_USER, "password": "123"}).status_code == 422
    assert client.post("/auth/register", json={**NEW_USER, "email": "nope"}).status_code == 422
    assert client.post("/auth/register", json={**NEW_USER, "username": "ab"}).status_code == 422


def test_login_returns_a_bearer_token(client):
    client.post("/auth/register", json=NEW_USER)
    response = client.post("/auth/login", data={"username": "carol", "password": "secret123"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer" and response.json()["access_token"]


def test_login_rejects_a_wrong_password_and_unknown_user_alike(client):
    client.post("/auth/register", json=NEW_USER)
    wrong = client.post("/auth/login", data={"username": "carol", "password": "wrongpass"})
    unknown = client.post("/auth/login", data={"username": "nobody", "password": "secret123"})
    assert wrong.status_code == unknown.status_code == 400
    assert wrong.json() == unknown.json()  # does not reveal which usernames exist


def test_me_returns_the_logged_in_user(client):
    headers = register_and_login(client, "dave")
    assert client.get("/users/me", headers=headers).json()["username"] == "dave"


def test_protected_routes_require_a_valid_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/trips").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/users/me", headers=bad).status_code == 401
