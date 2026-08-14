from __future__ import annotations

from unittest.mock import MagicMock, patch

from oh_my_ruyi.helper.main import main as helper_main
from oh_my_ruyi.infra.helper_client import PrivilegedHelperClient


def test_privileged_helper_client_run_as_root() -> None:
    client = PrivilegedHelperClient()
    mock_res = MagicMock(returncode=0, stdout="success", stderr="")
    with patch("subprocess.run", return_value=mock_res):
        ret, stdout, stderr = client.run_as_root(["echo", "hello"])

    assert ret == 0
    assert stdout == "success"
    assert stderr == ""


def test_helper_main_flash_command(capsys, tmp_path) -> None:
    img_file = tmp_path / "test.img"
    img_file.write_bytes(b"dummy")
    dev_file = tmp_path / "sdb"
    dev_file.write_bytes(b"dummy")

    mock_res = MagicMock(returncode=0, stdout="flashed", stderr="")
    with (
        patch("subprocess.run", return_value=mock_res),
        patch(
            "sys.argv",
            [
                "helper",
                "flash",
                "--device",
                str(dev_file),
                "--image",
                str(img_file),
            ],
        ),
    ):
        ret = helper_main()

    assert ret == 0
    captured = capsys.readouterr()
    assert f"Executing: dd if={img_file} of={dev_file}" in captured.out


def test_helper_main_no_command() -> None:
    with patch("sys.argv", ["helper"]):
        ret = helper_main()

    assert ret == 1
