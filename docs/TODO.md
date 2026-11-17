# TODO: Demo Monitoring Infrastructure (Linux)

Incremental checklist for AI-assisted development. Complete one checkbox (or one small group) per step. Keep each step locally runnable. Aligns with [requirements.md](requirements.md).

---

## Phase 0 — Project init + basic UI

### 0.1 Scaffold project
- [x] Create app layout: `app.py` (or `app/` package), `templates/`, `static/`, `tests/`, `docs/`
- [x] Add `requirements.txt` with Flask (pin versions)
- [x] Add `.gitignore` (venv, `__pycache__`, `.env`, `*.db`, secrets)
- [x] **Security:** Do not commit secrets, passwords, or SSH keys; ignore `.env` and `*.pem`
- [x] **Docs:** Short `README.md` — what the demo is, how to create venv and run

### 0.2 Hello Flask + attractive shell UI
- [x] Minimal Flask app that serves a home/dashboard shell page
- [x] Base template + CSS (attractive, readable; server list placeholder)
- [x] Bind to `0.0.0.0` by default (reachable from other hosts)
- [x] **Security:** No debug exposure of secrets; debug off by default when network-exposed; document `FLASK_DEBUG`
- [x] **Docs:** Update README with `http://<host>:5000` and description of the shell UI

---

## Phase 1 — Sign-in + unit tests

### 1.1 Config & hashed admin password
- [x] Load config from environment / `.env.example` (e.g. `SECRET_KEY`, `ADMIN_PASSWORD`)
- [x] Hash password with Werkzeug (or bcrypt); never store plaintext
- [x] Seed default username `admin` at startup if needed
- [x] **Security:** Require `SECRET_KEY`; refuse weak/empty secret in non-demo notes; document demo password only in `.env.example` (not real secrets)
- [x] **Docs:** Document default login and how to set `ADMIN_PASSWORD` / hash

### 1.2 Login / logout routes
- [x] Login form (username + password)
- [x] Session-based auth after successful verify
- [x] Logout route clears session
- [x] Protect dashboard routes (redirect unauthenticated users to login)
- [x] **Security:** POST-only login; constant-time compare via library hash check; no password in logs/flash messages
- [x] **Docs:** Document login/logout flow in README

### 1.3 Auth unit tests
- [x] Test setup (pytest + Flask test client)
- [x] Tests: valid login, invalid login, protected route redirect, logout
- [x] **Security:** Assert failed login does not create session; assert protected pages return 302/401 when logged out
- [x] **Docs:** Add `pytest` command to README

### 1.4 CI — GitHub Actions (tests)
- [x] Add `.github/workflows/ci.yml`: install deps, run pytest on push/PR
- [x] Pin Python version (e.g. 3.11 or 3.12)
- [x] **Security:** No secrets in workflow logs; use dummy `SECRET_KEY` / test password as env in CI only
- [x] **Docs:** Note in README that CI runs tests on GitHub Actions

---

## Phase 2 — Data layer (SQLite inventory)

### 2.1 Database model
- [x] SQLite schema for servers: label, host, ssh_port, ssh_username, auth fields (password **or** key path — pick one primary)
- [x] Init DB on first run
- [x] **Security:** Mark credential columns clearly; never render secrets in HTML; plan to avoid logging them
- [x] **Docs:** Document schema and chosen SSH auth method (password vs key)

### 2.2 Repository helpers + tests
- [x] CRUD helper functions (create/read/update/delete)
- [x] Unit tests for CRUD (temp DB)
- [x] **Security:** Tests ensure raw passwords are not returned by list/serialize helpers used by UI
- [x] **Docs:** Brief note on where the DB file lives and that it is local/demo-only

---

## Phase 3 — Server inventory UI (CRUD)

### 3.1 List servers
- [x] Authenticated page listing servers (no secrets shown)
- [x] Empty state when none added
- [x] **Security:** Route behind login; CSRF consideration for later forms (Flask-WTF or token) — add simple CSRF if forms are introduced next
- [x] **Docs:** Update README with “add servers after login”

### 3.2 Add server form
- [x] Form with all required fields (label, host, port, username, auth)
- [x] Validate required fields server-side
- [x] **Security:** CSRF on form; do not echo password back; trim/validate host & port range
- [x] **Docs:** Document required fields

### 3.3 Edit + delete server
- [x] Edit form (prefill non-secret fields; password blank = keep existing)
- [x] Delete with confirm
- [x] **Security:** POST for delete; authorize all mutations (logged-in only); never expose stored password to client
- [x] **Docs:** Document edit/delete behavior for credentials

### 3.4 Inventory tests + CI stay green
- [x] Tests for add/edit/delete via test client (authenticated)
- [x] **Security:** Tests that unauthenticated POST to CRUD is rejected
- [x] **Docs:** Mention inventory tests in README if useful

---

## Phase 4 — SSH client (read-only)

### 4.1 SSH connection helper
- [x] Paramiko (or equivalent) connect using stored credentials
- [x] Timeouts; clear error types (auth fail, timeout, unreachable)
- [x] **Security:** Read-only remote commands only; no shell write/upload; disable agent forwarding; document host-key policy for demo (e.g. AutoAddPolicy with warning)
- [x] **Docs:** Document SSH prerequisites (reachable host, user, auth)

### 4.2 SSH helper unit tests
- [x] Mock Paramiko: success path + auth failure + timeout
- [x] **Security:** Ensure command wrapper only allows a fixed allowlist of commands (no user-supplied shell strings)
- [x] **Docs:** Note that tests mock SSH (no real hosts needed in CI)

---

## Phase 5 — Metrics collection (one metric at a time)

### 5.1 Uptime
- [x] Fetch + parse uptime over SSH
- [x] Show on server detail page
- [x] **Security:** Fixed command allowlist entry only
- [x] **Docs:** What uptime displays

### 5.2 CPU
- [x] Fetch CPU % and/or load averages
- [x] **Security:** Allowlisted commands; parse safely
- [x] **Docs:** CPU fields explained

### 5.3 Memory
- [x] Fetch used/total/available
- [x] **Security:** Same as above
- [x] **Docs:** Memory fields explained

### 5.4 Disk
- [x] Fetch disk usage (root or mounts)
- [x] **Security:** Same as above
- [x] **Docs:** Disk fields explained

### 5.5 Network
- [ ] Fetch simple RX/TX or interface snapshot
- [ ] **Security:** Same as above
- [ ] **Docs:** Network fields explained

### 5.6 Ports
- [ ] Fetch listening ports
- [ ] **Security:** Read-only; no port scanning of third parties — only local `ss`/`netstat` on the target via SSH
- [ ] **Docs:** How ports are listed

### 5.7 Process list
- [ ] Top 20 processes by CPU
- [ ] **Security:** Do not run arbitrary user process filters from query string without validation
- [ ] **Docs:** Process list limits (top 20)

### 5.8 Metrics parser tests
- [x] Unit tests with sample command output fixtures (no live SSH)
- [x] **Security:** Parsers handle malformed output without crashing / leaking stack traces to clients
- [x] **Docs:** Note fixture-based metric tests

---

## Phase 6 — Server detail UI + errors

### 6.1 Detail page
- [x] Per-server page showing all metrics sections
- [x] Last refresh timestamp
- [x] **Security:** Auth required; never show SSH password/key material on detail page
- [x] **Docs:** Navigate list → detail

### 6.2 Friendly SSH errors
- [x] Show auth/timeout/unreachable messages in UI; app stays up
- [x] **Security:** Generic messages to client; detailed errors only in server logs (no credentials in logs)
- [x] **Docs:** Common failure reasons

---

## Phase 7 — Auto-refresh

### 7.1 Polling
- [x] Auto-refresh detail (and optionally list) every **15 seconds** (JS or meta refresh)
- [x] Preserve usability (don’t reset scroll harshly if easy)
- [x] **Security:** Refresh hits same authenticated endpoints only; no CORS wildcards needed for local demo
- [x] **Docs:** Document 15s default interval

---

## Phase 8 — Polish, security pass, CI/CD complete

### 8.1 UI polish
- [ ] Consistent layout, empty/loading/error states
- [ ] Read-only labeling where helpful
- [ ] **Docs:** Quick demo walkthrough (login → add server → view metrics)

### 8.2 Security checklist (demo-appropriate)
- [ ] Confirm metrics UI cannot mutate remote hosts
- [ ] Confirm `.gitignore` covers DB, `.env`, keys
- [ ] Confirm Flask binds `0.0.0.0` by default (network-reachable demo)
- [ ] Optional: add `pip-audit` or `safety` step in CI (non-blocking OK for demo)
- [ ] **Docs:** Short “Security notes (demo)” section in README

### 8.3 CI/CD finalize (GitHub Actions)
- [ ] CI runs: install → pytest (all tests)
- [ ] Optional job: lint (`ruff` or `flake8`) if already low-cost
- [ ] No deploy job required (local demo only) — document “no remote deploy”
- [ ] **Security:** CI uses env secrets pattern only for placeholders; nothing production-sensitive
- [ ] **Docs:** Link to workflow file; badge optional

### 8.4 Final acceptance vs PRD
- [ ] Login as `admin`
- [ ] Add / edit / delete server
- [ ] View CPU, memory, disk, network, ports, uptime, processes over SSH
- [ ] Auto-refresh works
- [ ] **Docs:** Mark success criteria done in README or keep PRD as source of truth

---

## Suggested order for AI sessions

1. Phase 0 (init + UI shell)  
2. Phase 1 (auth + tests + first CI)  
3. Phase 2 → 3 (DB + CRUD)  
4. Phase 4 → 5 (SSH + metrics one-by-one)  
5. Phase 6 → 7 (detail UI + auto-refresh)  
6. Phase 8 (polish + security + CI finalize)

---

## Out of scope (do not add TODO items)

Alerting, history/graphs, agents, Windows, SSO/LDAP, production deploy, secret vaults.
