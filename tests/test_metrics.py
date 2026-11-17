"""Parser and allowlist tests (no live SSH)."""

from metrics import (
    parse_cpu_from_top,
    parse_disk,
    parse_loadavg,
    parse_memory_free,
    parse_network,
    parse_ports,
    parse_processes,
    parse_uptime,
)
from ssh_client import COMMANDS


TOP_SAMPLE = """
top - 12:00:00 up 1 day,  1:00,  1 user,  load average: 0.10, 0.20, 0.30
Tasks: 100 total
%Cpu(s):  4.2 us,  1.3 sy,  0.0 ni, 94.0 id,  0.5 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   7950.0 total
"""

FREE_SAMPLE = """
              total        used        free      shared  buff/cache   available
Mem:           7950        2100        1000         100        4850        5500
Swap:          2047           0        2047
"""


def test_parse_cpu():
    assert parse_cpu_from_top(TOP_SAMPLE) == 5.5


def test_parse_cpu_malformed():
    assert parse_cpu_from_top("") is None
    assert parse_cpu_from_top("no cpu here") is None


def test_parse_memory():
    mem = parse_memory_free(FREE_SAMPLE)
    assert mem["total_mb"] == 7950
    assert mem["used_mb"] == 2100
    assert mem["available_mb"] == 5500
    assert mem["used_pct"] == 26.4


def test_parse_load_uptime_disk():
    assert parse_loadavg("0.10 0.20 0.30 1/100 123")["1m"] == 0.1
    assert parse_uptime("90061.45 12345.00") == "1d 1h 1m"
    disk = parse_disk("Filesystem Size Used Avail Use% Mounted\n/dev/sda1 50G 20G 28G 42% /\n")
    assert disk["use_pct"] == "42%"


def test_commands_are_fixed_allowlist():
    assert "cpu_top" in COMMANDS
    assert "memory" in COMMANDS
    # No format placeholders that would accept user input
    for cmd in COMMANDS.values():
        assert "{" not in cmd


def test_parse_network_and_processes():
    net = parse_network(
        "Inter-|   Receive\n"
        " face |bytes\n"
        "  eth0: 2048 0 0 0 0 0 0 0 4096 0 0 0 0 0 0 0\n"
        "    lo: 100 0 0 0 0 0 0 0 100 0 0 0 0 0 0 0\n"
    )
    assert net["rx_bytes"] == 2048
    assert net["tx_bytes"] == 4096

    procs = parse_processes("PID USER %CPU %MEM COMMAND\n1 root 0.0 0.1 systemd\n")
    assert procs[0]["comm"] == "systemd"


def test_parse_ports_ss():
    sample = (
        "State Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
        "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
        "LISTEN 0 128 127.0.0.1:5432 0.0.0.0:*\n"
    )
    ports = parse_ports(sample)
    assert ports["total"] >= 2
    assert ports["tcp"] >= 2
