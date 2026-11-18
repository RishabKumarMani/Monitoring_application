"""Localhost collector tests."""

from local_client import is_local_host, run_many_local
from metrics import collect_all_metrics


def test_is_local_host():
    assert is_local_host("localhost")
    assert is_local_host("127.0.0.1")
    assert is_local_host("::1")
    assert not is_local_host("10.0.0.5")


def test_run_many_local_memory():
    raw = run_many_local(["memory", "loadavg"])
    assert raw["memory"] and "Mem:" in raw["memory"]
    assert raw["loadavg"]


def test_collect_localhost_without_ssh():
    metrics = collect_all_metrics("127.0.0.1", 22, "anyone", "", auth_method="none")
    assert metrics["ok"] is True
    assert metrics["source"] == "local"
    assert metrics["memory"] is not None or metrics["load"] is not None
