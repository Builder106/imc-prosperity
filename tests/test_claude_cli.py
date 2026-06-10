from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from src.rag.claude_cli import run_claude_cli


def test_run_claude_cli_invokes_prompt_command():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=["claude", "-p", "hello"],
            returncode=0,
            stdout="response text\n",
            stderr="",
        )

        result = run_claude_cli("hello", cli_command="claude", timeout_seconds=5)

    assert result == "response text"
    mock_run.assert_called_once_with(
        ["claude", "-p", "hello"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_run_claude_cli_raises_on_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=["claude", "-p", "hello"],
            returncode=1,
            stdout="",
            stderr="command failed",
        )

        with pytest.raises(RuntimeError, match="command failed"):
            run_claude_cli("hello", cli_command="claude", timeout_seconds=5)
