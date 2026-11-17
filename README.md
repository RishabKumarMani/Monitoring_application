# Demo Monitoring Infrastructure (Linux)

Local demo web app for viewing Linux server metrics (CPU, memory, disk, network, ports, uptime, processes) in a read-only browser UI instead of SSHing in for routine checks.

**Audience:** Internal L1 / L2 / L3 infrastructure and application teams.  
**Scope:** Demo only — runs on the machine where Cursor is running. See [docs/requirements.md](docs/requirements.md) and [docs/TODO.md](docs/TODO.md).

## Current status

- Sign-in with `admin` + hashed password
- **Dashboard** shows live **CPU** and **memory** per host (SSH)
- **Add / Edit / Delete** Linux servers (SSH password auth)
- Server **detail** page: CPU, memory, load, uptime, disk
- Auto-refresh every 15 seconds
- SQLite inventory in `data/monitoring.db` (local demo only)
- Unit tests + GitHub Actions CI

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional; defaults work for local demo
python app.py
```

Open `http://<this-host-ip>:5000` → redirected to **Sign in**.

| Field | Demo default |
|-------|----------------|
| Username | `admin` |
| Password | `admin` (from `ADMIN_PASSWORD`, hashed at startup) |

After login you land on the **Dashboard**. Use **Add server** to register a Linux host (label, host/IP, SSH port, username, password). The dashboard SSHes to each host (read-only allowlisted commands) and shows CPU % and memory. Open **Details** for uptime/disk. Targets must be reachable over SSH from this machine.

Passwords are stored in the local SQLite DB and are **never** shown in the UI. Edit keeps the existing password if you leave the field blank.

Optional env: `FLASK_HOST` (default `0.0.0.0`), `FLASK_PORT` (default `5000`), `FLASK_DEBUG` (`1` to enable; **off** by default), `SECRET_KEY`, `ADMIN_PASSWORD`.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

CI runs the same tests on push/PR via [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (Python 3.12, dummy `SECRET_KEY` / `ADMIN_PASSWORD` env only).

## Security notes (demo)

- Do **not** commit `.env`, passwords, or SSH keys (see `.gitignore`).
- Password is verified with Werkzeug **hashed** check; plaintext is never stored in the app config as the credential of record.
- Login is **POST-only**; failed login shows a generic “Invalid credentials” message (no password in flashes/logs).
- Dashboard routes require a session; unauthenticated users are redirected to `/login`.
- Set a strong `SECRET_KEY` and `ADMIN_PASSWORD` in `.env` before any shared use. Empty `SECRET_KEY` falls back to a demo placeholder — change it.
- Binds to `0.0.0.0` by default — trusted demo network only.
- Keep `FLASK_DEBUG=0` when network-exposed.

## Project layout

```
app.py                 # Flask factory + auth + server CRUD
db.py                  # SQLite inventory helpers
templates/             # login, dashboard, server form
static/css/            # Styles
data/                  # monitoring.db (gitignored)
tests/                 # pytest (auth + inventory)
.github/workflows/     # CI
docs/                  # PRD + TODO
.env.example           # Demo env template
requirements.txt
```
