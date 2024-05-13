import subprocess
import sys

from visr import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "visr", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
