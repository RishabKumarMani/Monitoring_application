"""SQLite inventory for monitored Linux servers (local demo only)."""

import sqlite3
from pathlib import Path

# Primary SSH auth for this demo: password (stored in DB; never rendered in HTML)


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                host TEXT NOT NULL,
                ssh_port INTEGER NOT NULL,
                ssh_username TEXT NOT NULL,
                ssh_password TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _row_public(row):
    """Serialize for UI — excludes ssh_password."""
    return {
        "id": row["id"],
        "label": row["label"],
        "host": row["host"],
        "ssh_port": row["ssh_port"],
        "ssh_username": row["ssh_username"],
    }


def list_servers(db_path):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, label, host, ssh_port, ssh_username FROM servers ORDER BY label"
        ).fetchall()
    return [_row_public(r) for r in rows]


def get_server(db_path, server_id, include_secret=False):
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM servers WHERE id = ?", (server_id,)
        ).fetchone()
    if row is None:
        return None
    data = _row_public(row)
    if include_secret:
        data["ssh_password"] = row["ssh_password"]
    return data


def create_server(db_path, label, host, ssh_port, ssh_username, ssh_password):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO servers (label, host, ssh_port, ssh_username, ssh_password)
            VALUES (?, ?, ?, ?, ?)
            """,
            (label, host, ssh_port, ssh_username, ssh_password),
        )
        conn.commit()
        return cur.lastrowid


def update_server(
    db_path, server_id, label, host, ssh_port, ssh_username, ssh_password=None
):
    """If ssh_password is None or empty, keep the existing password."""
    existing = get_server(db_path, server_id, include_secret=True)
    if existing is None:
        return False
    password = ssh_password if ssh_password else existing["ssh_password"]
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE servers
            SET label = ?, host = ?, ssh_port = ?, ssh_username = ?, ssh_password = ?
            WHERE id = ?
            """,
            (label, host, ssh_port, ssh_username, password, server_id),
        )
        conn.commit()
    return True


def delete_server(db_path, server_id):
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        conn.commit()
        return cur.rowcount > 0
