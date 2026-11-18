# Demo Monitoring Infrastructure (Linux)

[![CI](https://github.com/RishabKumarMani/Monitoring_application/actions/workflows/ci.yml/badge.svg)](https://github.com/RishabKumarMani/Monitoring_application/actions/workflows/ci.yml)

Local **Host Monitor** demo: view Linux server metrics (CPU, memory, disk, load, network, ports, uptime, processes) in a read-only browser UI instead of SSHing in for routine checks.

**Audience:** Internal L1 / L2 / L3 infrastructure and application teams.  
**Scope:** Demo only — run on the machine where Cursor is running. **No remote production deploy.**  
See [docs/requirements.md](docs/requirements.md) and [docs/TODO.md](docs/TODO.md).

## Current status (acceptance)

| Criterion | Status |
|-----------|--------|
| Login as `admin` | Done |
| Add / edit / delete servers | Done |
| View CPU, memory, disk, network, ports, uptime, processes over SSH | Done |
| Auto-refresh (15s) | Done |
| GitHub Actions CI (pytest) | Done |

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
python app.py
```

Open `http://<this-host-ip>:5000` (default bind `0.0.0.0:5000`).

| Field | Demo default |
|-------|----------------|
| Username | `admin` |
| Password | `admin` (from `ADMIN_PASSWORD`, hashed at startup) |

### Demo walkthrough

1. Sign in as `admin` / `admin`.
2. Click **Add server** — enter label, host/IP, SSH port, username, and choose **SSH authentication**: Password or Without password (uses keys/agent on this machine).
3. On the dashboard, select the server chip — metric cards fill.
   For **localhost** / **127.0.0.1**, metrics are collected locally (no SSH; this machine has no sshd). Remote hosts still use SSH.
4. Edit / delete from the inventory actions; password blank on edit keeps the existing one.
5. Leave the page open — it auto-refreshes every **15 seconds**.

Optional env: `FLASK_HOST` (default `0.0.0.0`), `FLASK_PORT` (default `5000`), `FLASK_DEBUG` (`1` to enable; **off** by default), `SECRET_KEY`, `ADMIN_PASSWORD`.

## Metrics (read-only SSH)

Collection uses Paramiko with a **fixed command allowlist** (no user-supplied shell strings). Host-key policy for this demo is `AutoAddPolicy` — do not reuse that in production.

| Panel | Source | What you see |
|-------|--------|----------------|
| CPU | `top -bn1` | Approx. used % (us+sy) |
| Memory | `free -m` | Used %, used/free/total MiB |
| Disk | `df -h /` | Root filesystem use |
| Load | `/proc/loadavg` | 1 / 5 / 15 min |
| Network | `/proc/net/dev` | Cumulative RX / TX (excludes `lo`) |
| Ports | `ss` / `netstat` | Listening TCP/UDP **on the target only** (not a network scan) |
| Processes | `ps … \| head` | Top **20** by CPU |
| Uptime | `/proc/uptime` | Shown in the process panel footer |

SQLite inventory file: `data/monitoring.db` (gitignored, local demo only). SSH auth: **Password** or **Without password** (local SSH keys / agent).

## Tests & CI

```bash
source .venv/bin/activate
pytest -q
```

CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

- Install deps → **pytest**
- Optional **ruff** lint and **pip-audit** (non-blocking)
- Dummy `SECRET_KEY` / `ADMIN_PASSWORD` env only — nothing production-sensitive
- **No deploy job** (local demo only)

SSH is mocked in unit tests; CI does not need live hosts.

## Security notes (demo)

- Do **not** commit `.env`, DB files, passwords, or SSH keys (see `.gitignore`: `.env`, `data/`, `*.pem`, `*.key`, `id_rsa*`).
- Metrics UI is **read-only**: remote commands are allowlisted; no uploads, no agent forwarding, no arbitrary shell from the browser.
- Admin password verified with Werkzeug **hash** check; SSH passwords stored in local SQLite for demo and **never** rendered in HTML.
- Login is **POST-only**; failed login uses a generic message.
- CSRF tokens on mutating forms; mutations require a logged-in session.
- Binds to `0.0.0.0` by default — use only on a trusted demo network; keep `FLASK_DEBUG=0`.

## Project layout

```
app.py                 # Flask factory + auth + server CRUD + dashboard
db.py                  # SQLite inventory helpers
ssh_client.py          # Paramiko allowlisted runner
metrics.py             # Parsers + collectors
templates/             # Host Monitor UI
static/css/            # Dark dashboard styles
data/                  # monitoring.db (gitignored)
tests/                 # pytest
.github/workflows/     # CI (no deploy)
docs/                  # PRD + TODO
```
