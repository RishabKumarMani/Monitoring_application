"""Demo Monitoring Infrastructure — local Flask entrypoint."""

import os
import secrets
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import db as inventory
from metrics import collect_all_metrics

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ADMIN_USERNAME = "admin"


def create_app(test_config=None):
    """Application factory (used by runtime and pytest)."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)
    else:
        secret = os.environ.get("SECRET_KEY", "").strip()
        if not secret:
            # Demo fallback — set SECRET_KEY in .env for anything shared
            secret = "dev-only-change-me"
        app.config["SECRET_KEY"] = secret

        admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
        app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(admin_password)

        default_db = Path(app.root_path) / "data" / "monitoring.db"
        app.config["DATABASE"] = os.environ.get("DATABASE", str(default_db))

    # Ensure tests can inject a hash directly
    if "ADMIN_PASSWORD_HASH" not in app.config:
        pwd = app.config.get("ADMIN_PASSWORD", "admin")
        app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(pwd)

    if "DATABASE" not in app.config:
        app.config["DATABASE"] = str(Path(app.root_path) / "data" / "monitoring.db")

    inventory.init_db(app.config["DATABASE"])

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    def ensure_csrf():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        return session["csrf_token"]

    def validate_csrf():
        token = request.form.get("csrf_token", "")
        return token and token == session.get("csrf_token")

    def parse_server_form(require_password=True):
        label = (request.form.get("label") or "").strip()
        host = (request.form.get("host") or "").strip()
        username = (request.form.get("ssh_username") or "").strip()
        password = request.form.get("ssh_password") or ""
        port_raw = (request.form.get("ssh_port") or "").strip()
        auth_method = (request.form.get("auth_method") or "password").strip()
        if auth_method not in ("password", "none"):
            auth_method = "password"

        errors = []
        if not label:
            errors.append("Label is required.")
        if not host:
            errors.append("Hostname or IP is required.")
        try:
            port = int(port_raw)
            if not (1 <= port <= 65535):
                errors.append("SSH port must be between 1 and 65535.")
        except ValueError:
            port = None
            errors.append("SSH port must be a number.")
        if not username:
            errors.append("SSH username is required.")
        if auth_method == "password" and require_password and not password:
            errors.append("SSH password is required when auth method is Password.")
        if auth_method == "none":
            password = ""

        return {
            "label": label,
            "host": host,
            "ssh_port": port,
            "ssh_username": username,
            "ssh_password": password,
            "auth_method": auth_method,
            "errors": errors,
        }

    @app.before_request
    def _csrf_before():
        g.csrf_token = ensure_csrf()

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": ensure_csrf()}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("logged_in"):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            valid_user = username == ADMIN_USERNAME
            valid_pass = check_password_hash(
                app.config["ADMIN_PASSWORD_HASH"], password
            )

            if valid_user and valid_pass:
                session.clear()
                session["logged_in"] = True
                session["username"] = ADMIN_USERNAME
                ensure_csrf()
                next_url = request.args.get("next") or url_for("dashboard")
                if not next_url.startswith("/"):
                    next_url = url_for("dashboard")
                return redirect(next_url)

            # Do not echo username/password; generic message only
            flash("Invalid credentials.", "error")

        return render_template("login.html")

    @app.route("/logout", methods=["POST", "GET"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        servers = inventory.list_servers(app.config["DATABASE"])
        selected_id = request.args.get("server", type=int)
        selected = None
        metrics = None

        if servers:
            if selected_id and any(s["id"] == selected_id for s in servers):
                selected = inventory.get_server(
                    app.config["DATABASE"], selected_id, include_secret=True
                )
            else:
                selected = inventory.get_server(
                    app.config["DATABASE"], servers[0]["id"], include_secret=True
                )
            metrics = collect_all_metrics(
                selected["host"],
                selected["ssh_port"],
                selected["ssh_username"],
                selected.get("ssh_password") or "",
                auth_method=selected.get("auth_method") or "password",
            )
            selected = {k: v for k, v in selected.items() if k != "ssh_password"}

        return render_template(
            "dashboard.html",
            servers=servers,
            selected=selected,
            metrics=metrics,
            username=session.get("username"),
            refresh_seconds=15,
        )

    @app.route("/servers/<int:server_id>")
    @login_required
    def server_detail(server_id):
        return redirect(url_for("dashboard", server=server_id))

    @app.route("/servers/add", methods=["GET", "POST"])
    @login_required
    def add_server():
        form = {
            "label": "",
            "host": "",
            "ssh_port": 22,
            "ssh_username": "",
            "ssh_password": "",
            "auth_method": "password",
        }
        if request.method == "POST":
            if not validate_csrf():
                flash("Invalid form token. Try again.", "error")
                return redirect(url_for("add_server"))

            parsed = parse_server_form(require_password=True)
            form.update(
                {
                    "label": parsed["label"],
                    "host": parsed["host"],
                    "ssh_port": parsed["ssh_port"] or 22,
                    "ssh_username": parsed["ssh_username"],
                    "auth_method": parsed["auth_method"],
                }
            )
            if parsed["errors"]:
                for err in parsed["errors"]:
                    flash(err, "error")
                return render_template(
                    "server_form.html",
                    mode="add",
                    form=form,
                    page_title="Add server",
                )

            inventory.create_server(
                app.config["DATABASE"],
                parsed["label"],
                parsed["host"],
                parsed["ssh_port"],
                parsed["ssh_username"],
                parsed["ssh_password"],
                auth_method=parsed["auth_method"],
            )
            flash("Server added.", "ok")
            return redirect(url_for("dashboard"))

        return render_template(
            "server_form.html",
            mode="add",
            form=form,
            page_title="Add server",
        )

    @app.route("/servers/<int:server_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_server(server_id):
        server = inventory.get_server(app.config["DATABASE"], server_id)
        if server is None:
            flash("Server not found.", "error")
            return redirect(url_for("dashboard"))

        form = {
            "label": server["label"],
            "host": server["host"],
            "ssh_port": server["ssh_port"],
            "ssh_username": server["ssh_username"],
            "ssh_password": "",
            "auth_method": server.get("auth_method") or "password",
        }

        if request.method == "POST":
            if not validate_csrf():
                flash("Invalid form token. Try again.", "error")
                return redirect(url_for("edit_server", server_id=server_id))

            parsed = parse_server_form(require_password=False)
            form.update(
                {
                    "label": parsed["label"],
                    "host": parsed["host"],
                    "ssh_port": parsed["ssh_port"] or server["ssh_port"],
                    "ssh_username": parsed["ssh_username"],
                    "auth_method": parsed["auth_method"],
                }
            )
            if parsed["errors"]:
                for err in parsed["errors"]:
                    flash(err, "error")
                return render_template(
                    "server_form.html",
                    mode="edit",
                    form=form,
                    server_id=server_id,
                    page_title="Edit server",
                )

            inventory.update_server(
                app.config["DATABASE"],
                server_id,
                parsed["label"],
                parsed["host"],
                parsed["ssh_port"],
                parsed["ssh_username"],
                parsed["ssh_password"] or None,
                auth_method=parsed["auth_method"],
            )
            flash("Server updated.", "ok")
            return redirect(url_for("dashboard"))

        return render_template(
            "server_form.html",
            mode="edit",
            form=form,
            server_id=server_id,
            page_title="Edit server",
        )

    @app.route("/servers/<int:server_id>/delete", methods=["POST"])
    @login_required
    def delete_server(server_id):
        if not validate_csrf():
            flash("Invalid form token. Try again.", "error")
            return redirect(url_for("dashboard"))

        if inventory.delete_server(app.config["DATABASE"], server_id):
            flash("Server deleted.", "ok")
        else:
            flash("Server not found.", "error")
        return redirect(url_for("dashboard"))

    return app


app = create_app()


if __name__ == "__main__":
    # Reachable on the network (0.0.0.0). Debug off by default when exposed.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=debug)
