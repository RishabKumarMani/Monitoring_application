"""Auth unit tests — login, logout, route protection."""


def test_dashboard_redirects_when_logged_out(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page_ok(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_valid_login_sets_session(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-pass"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        assert sess.get("logged_in") is True
        assert sess.get("username") == "admin"

    dash = client.get("/")
    assert dash.status_code == 200
    assert b"Monitoring dashboard" in dash.data


def test_invalid_login_does_not_create_session(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

    with client.session_transaction() as sess:
        assert not sess.get("logged_in")


def test_logout_clears_session(client):
    client.post("/login", data={"username": "admin", "password": "test-pass"})
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with client.session_transaction() as sess:
        assert not sess.get("logged_in")

    protected = client.get("/", follow_redirects=False)
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]


def test_login_get_does_not_authenticate(client):
    response = client.get("/login?username=admin&password=test-pass")
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert not sess.get("logged_in")
