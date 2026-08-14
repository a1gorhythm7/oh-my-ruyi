"""Client for the Privileged Helper process."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Protocol


class IPrivilegedHelperClient(Protocol):
    def run_as_root(self, cmd: list[str]) -> tuple[int, str, str]:
        """Runs a command as root via the helper, returning (returncode, stdout, stderr)."""
        ...


class PrivilegedHelperClient(IPrivilegedHelperClient):
    """Subprocess runner for privileged system helper commands."""

    def run_as_root(self, cmd: list[str]) -> tuple[int, str, str]:
        """Executes a command using sudo or direct execution if already root."""
        if not cmd:
            return (1, "", "empty command list")

        runner: list[str] = []
        if os.geteuid() != 0:
            if shutil.which("sudo"):
                runner = ["sudo", "-n"]
            elif shutil.which("pkexec"):
                runner = ["pkexec"]

        full_cmd = runner + cmd
        try:
            res = subprocess.run(full_cmd, text=True, capture_output=True)
            return (res.returncode, res.stdout, res.stderr)
        except Exception as exc:
            return (1, "", f"Failed to execute privileged helper: {exc}")
