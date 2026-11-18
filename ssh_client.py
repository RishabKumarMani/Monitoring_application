"""Read-only SSH helper (Paramiko). Commands must be allowlisted — no user shell strings."""

import logging

import paramiko

logger = logging.getLogger(__name__)

# Fixed allowlist only — never interpolate user input into commands
COMMANDS = {
    "cpu_top": "top -bn1",
    "memory": "free -m",
    "uptime": "cat /proc/uptime",
    "loadavg": "cat /proc/loadavg",
    "disk": "df -h /",
    "network": "cat /proc/net/dev",
    "ports": "ss -tuln 2>/dev/null || netstat -tuln 2>/dev/null",
    "processes": "ps -eo pid,user,%cpu,%mem,comm --sort=-%cpu | head -n 21",
}


class SSHError(Exception):
    """Base SSH error with a safe client-facing message."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class AuthFailed(SSHError):
    def __init__(self):
        super().__init__("auth", "SSH authentication failed.")


class Unreachable(SSHError):
    def __init__(self):
        super().__init__("unreachable", "Host unreachable or timed out.")


class CommandFailed(SSHError):
    def __init__(self):
        super().__init__("command", "Could not collect metrics.")


def _connect(client, host, port, username, password, auth_method, timeout):
    """Connect using password or passwordless (local keys / agent)."""
    use_password = (auth_method or "password") == "password"
    kwargs = {
        "hostname": host,
        "port": int(port),
        "username": username,
        "timeout": timeout,
        "auth_timeout": timeout,
        "banner_timeout": timeout,
    }
    if use_password:
        kwargs["password"] = password or ""
        kwargs["allow_agent"] = False
        kwargs["look_for_keys"] = False
    else:
        # Without password: try default key files and ssh-agent on this machine
        kwargs["password"] = None
        kwargs["allow_agent"] = True
        kwargs["look_for_keys"] = True
    client.connect(**kwargs)


def run_command(host, port, username, password, command_key, timeout=8, auth_method="password"):
    """Run an allowlisted command over SSH; return stdout text."""
    if command_key not in COMMANDS:
        raise ValueError(f"Command not allowlisted: {command_key}")

    client = paramiko.SSHClient()
    # Demo only: auto-add host keys. Do not use this policy in production.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        _connect(client, host, port, username, password, auth_method, timeout)
        _stdin, stdout, stderr = client.exec_command(
            COMMANDS[command_key], timeout=timeout
        )
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        status = stdout.channel.recv_exit_status()
        if status != 0 and not out.strip():
            logger.warning("SSH command %s failed on %s (status=%s)", command_key, host, status)
            if err:
                logger.debug("stderr suppressed in UI")
            raise CommandFailed()
        return out
    except paramiko.AuthenticationException as exc:
        raise AuthFailed() from exc
    except (paramiko.SSHException, OSError, TimeoutError) as exc:
        logger.warning("SSH connection issue to %s: %s", host, type(exc).__name__)
        raise Unreachable() from exc
    finally:
        client.close()


def run_many(host, port, username, password, command_keys, timeout=8, auth_method="password"):
    """Run several allowlisted commands on one connection."""
    for key in command_keys:
        if key not in COMMANDS:
            raise ValueError(f"Command not allowlisted: {key}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    results = {}

    try:
        _connect(client, host, port, username, password, auth_method, timeout)
        for key in command_keys:
            _stdin, stdout, stderr = client.exec_command(COMMANDS[key], timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            status = stdout.channel.recv_exit_status()
            if status != 0 and not out.strip():
                results[key] = None
            else:
                results[key] = out
        return results
    except paramiko.AuthenticationException as exc:
        raise AuthFailed() from exc
    except (paramiko.SSHException, OSError, TimeoutError) as exc:
        logger.warning("SSH connection issue to %s: %s", host, type(exc).__name__)
        raise Unreachable() from exc
    finally:
        client.close()
