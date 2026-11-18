"""Parse Linux command output into metrics. Safe against malformed input."""

import re
from datetime import datetime, timezone

from local_client import is_local_host, run_many_local
from ssh_client import SSHError, run_many

FULL_KEYS = [
    "cpu_top",
    "memory",
    "loadavg",
    "uptime",
    "disk",
    "network",
    "ports",
    "processes",
]


def parse_cpu_from_top(text):
    """Return CPU used % from `top -bn1` output, or None."""
    if not text:
        return None
    m = re.search(
        r"Cpu\(s\):\s*([\d.]+)\s*us[,\s]+([\d.]+)\s*sy",
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            return round(float(m.group(1)) + float(m.group(2)), 1)
        except ValueError:
            return None
    m = re.search(r"(\d+[.,]\d+)\s*%?us", text, re.IGNORECASE)
    if m:
        try:
            return round(float(m.group(1).replace(",", ".")), 1)
        except ValueError:
            return None
    return None


def parse_loadavg(text):
    if not text:
        return None
    parts = text.strip().split()
    if len(parts) < 3:
        return None
    try:
        return {
            "1m": float(parts[0]),
            "5m": float(parts[1]),
            "15m": float(parts[2]),
        }
    except ValueError:
        return None


def parse_memory_free(text):
    """Parse `free -m` → used/total/available in MiB."""
    if not text:
        return None
    for line in text.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            try:
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])
                available = int(parts[6]) if len(parts) > 6 else free
                return {
                    "total_mb": total,
                    "used_mb": used,
                    "free_mb": free,
                    "available_mb": available,
                    "used_pct": round((used / total) * 100, 1) if total else 0,
                }
            except (IndexError, ValueError, ZeroDivisionError):
                return None
    return None


def parse_uptime(text):
    if not text:
        return None
    try:
        seconds = float(text.strip().split()[0])
    except (ValueError, IndexError):
        return None
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def parse_disk(text):
    if not text:
        return None
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) < 5:
        return None
    return {
        "filesystem": parts[0],
        "size": parts[1],
        "used": parts[2],
        "avail": parts[3],
        "use_pct": parts[4],
        "mount": parts[5] if len(parts) > 5 else "/",
    }


def parse_network(text):
    """Sum RX/TX bytes from /proc/net/dev (skip lo)."""
    if not text:
        return None
    rx = tx = 0
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        iface = name.strip()
        if iface == "lo" or not iface:
            continue
        cols = rest.split()
        if len(cols) < 9:
            continue
        try:
            rx += int(cols[0])
            tx += int(cols[8])
        except ValueError:
            continue
    return {
        "rx": _human_bytes(rx),
        "tx": _human_bytes(tx),
        "rx_bytes": rx,
        "tx_bytes": tx,
    }


def _human_bytes(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def parse_ports(text):
    """Parse ss/netstat listening ports → list + counts."""
    if not text:
        return None
    ports = []
    tcp = udp = 0
    for line in text.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if not (lower.startswith("tcp") or lower.startswith("udp") or "listen" in lower):
            # ss format: State Recv-Q Send-Q Local Address:Port Peer
            pass
        parts = line.split()
        if len(parts) < 4:
            continue
        proto = parts[0].lower()
        # ss: State ... Local Address:Port
        # netstat: Proto ... Local Address Foreign
        local = parts[3] if "listen" in lower or proto.startswith("tcp") or proto.startswith("udp") else None
        if proto in ("tcp", "tcp6", "udp", "udp6"):
            local = parts[3] if len(parts) > 3 else ""
        elif parts[0].upper() in ("LISTEN", "UNCONN"):
            proto = parts[0]
            local = parts[3] if len(parts) > 3 else ""
            # ss without proto in first col — detect from local later
            if "tcp" in line.lower():
                proto = "tcp"
            elif "udp" in line.lower():
                proto = "udp"
        else:
            # ss: LISTEN 0 128 0.0.0.0:22 ...
            if parts[0] == "LISTEN":
                proto = "tcp"
                local = parts[3]
            elif parts[0] in ("UNCONN", "ESTAB"):
                continue
            else:
                continue

        if not local:
            continue
        port = local.rsplit(":", 1)[-1]
        if not port.isdigit():
            continue
        entry = {"proto": proto.replace("6", ""), "port": port, "local": local}
        if entry not in ports:
            ports.append(entry)
            if entry["proto"].startswith("udp"):
                udp += 1
            else:
                tcp += 1
    # Use "entries" (not "items") — Jinja treats .items as dict.items()
    return {"entries": ports[:40], "tcp": tcp, "udp": udp, "total": len(ports)}


def parse_processes(text):
    """Parse `ps` top processes (skip header)."""
    if not text:
        return None
    rows = []
    lines = text.strip().splitlines()
    for line in lines[1:21]:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        rows.append(
            {
                "pid": parts[0],
                "user": parts[1],
                "cpu": parts[2],
                "mem": parts[3],
                "comm": parts[4],
            }
        )
    return rows


def _empty_metrics(error=None, ok=False):
    return {
        "ok": ok,
        "error": error,
        "cpu_pct": None,
        "memory": None,
        "load": None,
        "uptime": None,
        "disk": None,
        "network": None,
        "ports": None,
        "processes": None,
        "fetched_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "source": None,
    }


def collect_all_metrics(host, port, username, password, auth_method="password"):
    """Full metric set for Host Monitor panels.

    localhost / 127.0.0.1 / ::1 are collected locally (no SSH) because sshd
    is often not running on the demo machine.
    """
    try:
        if is_local_host(host):
            raw = run_many_local(FULL_KEYS)
        else:
            raw = run_many(
                host,
                port,
                username,
                password,
                FULL_KEYS,
                auth_method=auth_method or "password",
            )
        return {
            "ok": True,
            "error": None,
            "cpu_pct": parse_cpu_from_top(raw.get("cpu_top")),
            "memory": parse_memory_free(raw.get("memory")),
            "load": parse_loadavg(raw.get("loadavg")),
            "uptime": parse_uptime(raw.get("uptime")),
            "disk": parse_disk(raw.get("disk")),
            "network": parse_network(raw.get("network")),
            "ports": parse_ports(raw.get("ports")),
            "processes": parse_processes(raw.get("processes")),
            "fetched_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "source": "local" if is_local_host(host) else "ssh",
        }
    except SSHError as exc:
        return _empty_metrics(error=str(exc), ok=False)


# Back-compat alias used by older imports
def collect_dashboard_metrics(host, port, username, password, auth_method="password"):
    return collect_all_metrics(host, port, username, password, auth_method=auth_method)
