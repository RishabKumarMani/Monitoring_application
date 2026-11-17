"""SSH helper unit tests with mocked Paramiko."""

from unittest.mock import MagicMock, patch

import pytest

from ssh_client import AuthFailed, COMMANDS, Unreachable, run_command


def test_rejects_non_allowlisted_command():
    with pytest.raises(ValueError, match="allowlisted"):
        run_command("h", 22, "u", "p", "rm -rf /")


@patch("ssh_client.paramiko.SSHClient")
def test_run_command_success(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    stdout = MagicMock()
    stdout.read.return_value = b"ok-output"
    stdout.channel.recv_exit_status.return_value = 0
    stderr = MagicMock()
    stderr.read.return_value = b""
    client.exec_command.return_value = (MagicMock(), stdout, stderr)

    out = run_command("10.0.0.1", 22, "user", "secret", "memory")
    assert out == "ok-output"
    client.connect.assert_called()
    assert client.connect.call_args.kwargs["allow_agent"] is False
    assert client.connect.call_args.kwargs["look_for_keys"] is False
    client.exec_command.assert_called_with(COMMANDS["memory"], timeout=8)


@patch("ssh_client.paramiko.SSHClient")
def test_auth_failure(mock_cls):
    import paramiko

    client = MagicMock()
    mock_cls.return_value = client
    client.connect.side_effect = paramiko.AuthenticationException("nope")
    with pytest.raises(AuthFailed):
        run_command("10.0.0.1", 22, "user", "bad", "memory")


@patch("ssh_client.paramiko.SSHClient")
def test_unreachable(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.connect.side_effect = TimeoutError("timeout")
    with pytest.raises(Unreachable):
        run_command("10.0.0.1", 22, "user", "secret", "memory")
