"""Run allowlisted metric commands on the local host (no SSH)."""

import logging
import subprocess

from ssh_client import COMMANDS, CommandFailed

logger = logging.getLogger(__name__)

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def is_local_host(host):
    return (host or "").strip().lower() in LOCAL_HOSTS


def run_many_local(command_keys, timeout=8):
    """Execute allowlisted commands locally via subprocess."""
    for key in command_keys:
        if key not in COMMANDS:
            raise ValueError(f"Command not allowlisted: {key}")

    results = {}
    for key in command_keys:
        try:
            completed = subprocess.run(
                COMMANDS[key],
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = completed.stdout or ""
            if completed.returncode != 0 and not out.strip():
                logger.warning("Local command %s failed (status=%s)", key, completed.returncode)
                results[key] = None
            else:
                results[key] = out
        except subprocess.TimeoutExpired as exc:
            logger.warning("Local command %s timed out", key)
            raise CommandFailed() from exc
    return results
