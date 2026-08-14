"""Privileged Helper Process.
This process must be launched via pkexec/sudo and handles destructive actions
(e.g., flashing the block device) and privilege elevation for the main UI.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys


def flash(device_path: str, image_path: str) -> int:
    """Executes block device flashing via dd with validation."""
    if not os.path.exists(image_path):
        sys.stderr.write(f"Error: image file '{image_path}' does not exist.\n")
        return 1

    if not os.path.exists(device_path):
        sys.stderr.write(f"Error: target device '{device_path}' does not exist.\n")
        return 1

    bs = "4M" if platform.system() == "Linux" else "1m"
    cmd = ["dd", f"if={image_path}", f"of={device_path}", f"bs={bs}"]
    if platform.system() == "Linux":
        cmd.extend(["status=progress", "conv=fsync"])

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Oh My Ruyi Privileged Helper")
    subparsers = parser.add_subparsers(dest="command")

    flash_parser = subparsers.add_parser("flash")
    flash_parser.add_argument("--device", required=True)
    flash_parser.add_argument("--image", required=True)

    args = parser.parse_args()

    if args.command == "flash":
        return flash(args.device, args.image)

    return 1


if __name__ == "__main__":
    sys.exit(main())
