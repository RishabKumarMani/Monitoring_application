# PRD: Demo Monitoring Infrastructure (Linux Servers)

## 1. Overview

Local demo web app that lets internal ops and app teams view live Linux server metrics in a browser instead of SSH’ing in for routine checks.

**Audience:** L1 / L2 / L3 infrastructure and application teams (internal only).  
**Deployment:** Run locally on the machine where Cursor is running.  
**Nature:** Demo — keep scope small, no production hardening beyond basic auth.

---

## 2. Problem

Today, checking real-time CPU, memory, disk, network, ports, uptime, and processes requires logging into each Linux server. That is slow, error-prone, and hard to share across teams.

---

## 3. Goals

- Show live Linux host metrics in a read-only UI.
- Add / edit / delete monitored servers via the UI.
- Collect metrics over SSH (no agent on targets).
- Protect the UI with a single admin login (hashed password).
- Auto-refresh so the dashboard stays current without manual reload.

**Non-goals (demo):** Multi-user RBAC, alerting, historical graphs/DB time-series, Windows hosts, cloud APIs, HA, or remote production deploy.

---

## 4. Users & Access

| Role | Access |
|------|--------|
| Admin (only user) | Sign in, manage servers, view all metrics (UI itself is read-only for metrics) |

- Default username: `admin`
- Password: stored hashed (e.g. Werkzeug / bcrypt); one seeded account is enough
- No password-change UI, no session-timeout policy required for demo
- Logout is optional but recommended if sessions are used

---

## 5. Core Features

### 5.1 Read-only monitoring UI

- Clean, attractive Flask-rendered UI (HTML/CSS; optional lightweight JS for refresh).
- Metrics views are read-only — no remote shell, no config changes on targets from the dashboard.
- List of servers + detail view per server.

### 5.2 Sign-in

- Login page with username + password.
- Default user: `admin` with hashed password verified on login.
- Unauthenticated users cannot access dashboard or server APIs.

### 5.3 Server inventory (CRUD)

Add / edit / delete Linux servers. All fields required:

| Field | Description |
|-------|-------------|
| Label / name | Display name |
| Hostname or IP | SSH target |
| SSH port | e.g. 22 |
| SSH username | Login user on the target |
| SSH auth | Password **or** private key path/content (pick one approach and stick to it in implementation) |

- Validate connectivity optionally on save (nice-to-have for demo).
- Store credentials only as needed for local demo (document that secrets are local/demo-only).

### 5.4 Metrics collected over SSH

For each server, gather via remote commands over SSH:

| Metric | User-facing content |
|--------|---------------------|
| CPU | Usage % (and optionally load averages) |
| Memory | Used / total / available |
| Disk | Usage per mount (or root at minimum) |
| Network | Interface RX/TX or simple traffic snapshot |
| Ports | Listening / open ports |
| Uptime | Host uptime |
| Processes | Process list (top N by CPU/memory is enough) |

Collection model: Flask backend opens SSH to the host, runs read-only commands, parses output, returns JSON/HTML to the UI.

### 5.5 Auto-refresh

- Dashboard / detail views refresh automatically on an interval (suggested default: **10–30 seconds**).
- No need for WebSockets; simple polling is fine.

---

## 6. Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3 |
| Web | Flask |
| UI | Attractive server-rendered templates (+ CSS; minimal JS for auto-refresh) |
| SSH | Paramiko (or equivalent) |
| Auth | Flask session + hashed password |
| Storage | SQLite (or JSON file) for server inventory — keep local and simple |

---

## 7. UX Notes

- Friendly layout: server cards/table → click into detail panels for metrics.
- Clear status: last refresh time, SSH success/failure per host.
- Errors (SSH timeout, auth failure) shown in UI without crashing the app.

---

## 8. Success Criteria (demo)

1. Start the app locally and sign in as `admin`.
2. Add 1–2 Linux hosts with required SSH fields.
3. Without manual SSH, view CPU, memory, disk, network, ports, uptime, and process list.
4. Metrics update automatically on the refresh interval.
5. Edit and delete a server from the UI.

---

## 9. Local Run (minimal)

```bash
# from project root
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the URL printed by Flask (typically `http://<host>:5000`), sign in as `admin`, add a server, view metrics.

**Assumptions:** Targets are reachable over SSH from this machine; Python 3 is installed.

---

## 10. Out of Scope

- Alerts / email / Slack
- Historical charts and long-term retention
- Agent-based collection
- Non-Linux OS
- Multi-tenant or LDAP/SSO
- Production TLS, secret vaults, audit logs

---

## 11. Open Implementation Choices (acceptable defaults)

- Auto-refresh interval: **15 seconds**
- Process list: top **20** by CPU
- SSH auth for demo: password **or** key — implement one primary method; document which
- Persist inventory in **SQLite**
