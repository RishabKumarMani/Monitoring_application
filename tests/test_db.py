"""SQLite inventory unit tests."""

import db as inventory


def test_crud_and_public_list_hides_password(tmp_path):
    path = str(tmp_path / "inv.db")
    inventory.init_db(path)

    sid = inventory.create_server(
        path, "web1", "10.0.0.5", 22, "ubuntu", "s3cret"
    )
    assert sid > 0

    listed = inventory.list_servers(path)
    assert len(listed) == 1
    assert listed[0]["label"] == "web1"
    assert "ssh_password" not in listed[0]

    public = inventory.get_server(path, sid, include_secret=False)
    assert "ssh_password" not in public

    secret = inventory.get_server(path, sid, include_secret=True)
    assert secret["ssh_password"] == "s3cret"

    inventory.update_server(path, sid, "web1b", "10.0.0.6", 2222, "ops", None)
    updated = inventory.get_server(path, sid, include_secret=True)
    assert updated["label"] == "web1b"
    assert updated["host"] == "10.0.0.6"
    assert updated["ssh_port"] == 2222
    assert updated["ssh_password"] == "s3cret"  # kept when blank

    inventory.update_server(path, sid, "web1b", "10.0.0.6", 2222, "ops", "newpass")
    assert inventory.get_server(path, sid, include_secret=True)["ssh_password"] == "newpass"

    assert inventory.delete_server(path, sid) is True
    assert inventory.list_servers(path) == []


def test_create_without_password_auth(tmp_path):
    path = str(tmp_path / "inv2.db")
    inventory.init_db(path)
    sid = inventory.create_server(
        path, "nopw", "10.0.0.9", 22, "ubuntu", "", auth_method="none"
    )
    row = inventory.get_server(path, sid, include_secret=True)
    assert row["auth_method"] == "none"
    assert row["ssh_password"] == ""
    public = inventory.list_servers(path)[0]
    assert public["auth_method"] == "none"
    assert "ssh_password" not in public
