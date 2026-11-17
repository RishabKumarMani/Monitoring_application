"""Server inventory UI tests."""


def _csrf(client):
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def test_dashboard_lists_servers(auth_client, app):
    import db as inventory

    inventory.create_server(
        app.config["DATABASE"],
        "api",
        "192.168.1.10",
        22,
        "admin",
        "s3cr3t-password-xyz",
    )
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Add server" in response.data
    assert b"api" in response.data
    assert b"192.168.1.10" in response.data
    assert b"s3cr3t-password-xyz" not in response.data


def test_add_server_form_and_create(auth_client):
    get = auth_client.get("/servers/add")
    assert get.status_code == 200
    assert b"Add server" in get.data

    token = _csrf(auth_client)
    response = auth_client.post(
        "/servers/add",
        data={
            "csrf_token": token,
            "label": "db1",
            "host": "10.1.1.2",
            "ssh_port": "22",
            "ssh_username": "ubuntu",
            "ssh_password": "pw",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    dash = auth_client.get("/")
    assert b"db1" in dash.data
    assert b"pw" not in dash.data


def test_edit_and_delete_server(auth_client, app):
    import db as inventory

    sid = inventory.create_server(
        app.config["DATABASE"], "old", "10.0.0.1", 22, "root", "keepme"
    )
    token = _csrf(auth_client)

    edit = auth_client.post(
        f"/servers/{sid}/edit",
        data={
            "csrf_token": token,
            "label": "new",
            "host": "10.0.0.2",
            "ssh_port": "22",
            "ssh_username": "root",
            "ssh_password": "",
        },
        follow_redirects=True,
    )
    assert edit.status_code == 200
    assert b"new" in edit.data
    assert inventory.get_server(app.config["DATABASE"], sid, include_secret=True)[
        "ssh_password"
    ] == "keepme"

    token = _csrf(auth_client)
    deleted = auth_client.post(
        f"/servers/{sid}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert b"old" not in deleted.data
    assert b"new" not in deleted.data


def test_unauthenticated_crud_rejected(client):
    response = client.post(
        "/servers/add",
        data={
            "label": "x",
            "host": "1.2.3.4",
            "ssh_port": "22",
            "ssh_username": "u",
            "ssh_password": "p",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
