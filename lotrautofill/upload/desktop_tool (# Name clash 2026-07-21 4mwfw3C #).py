"""Install and run the chilli-axe/mpc-autofill desktop tool on an order.xml.

This wraps the proven desktop tool so a LOTRAutofill user can go from an
``order.xml`` to a MakePlayingCards project (or a PDF proof) in one command.
The tool is cloned once and given its own virtualenv; subsequent runs reuse it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/chilli-axe/mpc-autofill.git"
DEFAULT_TOOL_DIR = Path.home() / ".lotr-autofill" / "mpc-autofill"

# Packages in the tool's requirements.txt that are build/dev-only — skipped so
# the one-time install stays fast (nuitka in particular compiles from source).
_DEV_ONLY = {"nuitka", "pre-commit", "coverage", "pytest", "pytest-retry"}


def default_tool_dir() -> Path:
    return DEFAULT_TOOL_DIR


def _host_python() -> str:
    """A real Python interpreter to build the tool's venv with.

    When LOTRAutofill runs as a frozen executable, ``sys.executable`` is the
    .exe, not a Python — so fall back to a Python found on PATH (the desktop
    tool needs Python anyway).
    """
    if not getattr(sys, "frozen", False):
        return sys.executable
    for name in ("python", "python3", "py"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(
        "Python is required to run the mpc-autofill desktop tool but none was "
        "found on PATH. Install Python 3.10+ and try again."
    )


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_tool(tool_dir: Path, skip_install: bool = False) -> Path:
    """Clone the repo (if needed) and build its venv. Returns desktop-tool dir."""
    tool_dir = Path(tool_dir)
    if not (tool_dir / ".git").exists():
        tool_dir.parent.mkdir(parents=True, exist_ok=True)
        if tool_dir.exists() and any(tool_dir.iterdir()):
            raise RuntimeError(f"{tool_dir} exists and is not a git checkout.")
        print(f"Cloning mpc-autofill into {tool_dir} ...")
        _run(["git", "clone", "--depth", "1", REPO_URL, str(tool_dir)])

    desktop = tool_dir / "desktop-tool"
    if not desktop.is_dir():
        raise RuntimeError(f"desktop-tool folder not found under {tool_dir}")

    if not skip_install:
        venv_dir = desktop / ".venv"
        if not _venv_python(venv_dir).exists():
            print("Creating virtualenv and installing requirements (one-time) ...")
            _run([_host_python(), "-m", "venv", str(venv_dir)])
            py = str(_venv_python(venv_dir))
            _run([py, "-m", "pip", "install", "--upgrade", "pip"])
            reqs = _runtime_requirements(desktop / "requirements.txt")
            _run([py, "-m", "pip", "install", *reqs])
    return desktop


def _runtime_requirements(requirements_txt: Path) -> list[str]:
    """Requirement lines with build/dev-only packages removed."""
    reqs: list[str] = []
    for line in requirements_txt.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("~=")[0].split("==")[0].split(">=")[0].split("<")[0].strip()
        if name.lower() not in _DEV_ONLY:
            reqs.append(line)
    return reqs


def run_autofill(
    order_xml: Path,
    tool_dir: Path = DEFAULT_TOOL_DIR,
    browser: str = "chrome",
    export_pdf: bool = False,
    skip_install: bool = False,
    extra_args: list[str] | None = None,
) -> int:
    """Run the desktop tool against a single order.xml."""
    order_xml = Path(order_xml).resolve()
    if not order_xml.is_file():
        print(f"error: order file not found: {order_xml}", file=sys.stderr)
        return 2

    desktop = ensure_tool(tool_dir, skip_install=skip_install)
    py = _venv_python(desktop / ".venv")
    runner = str(py) if py.exists() else sys.executable

    # The tool reads every *.xml in its working directory; give it a clean one.
    workdir = Path(tempfile.mkdtemp(prefix="lotr-order-"))
    shutil.copy2(order_xml, workdir / order_xml.name)

    cmd = [runner, "autofill.py", "-d", str(workdir), "-b", browser]
    if export_pdf:
        cmd.append("--exportpdf")
    cmd += extra_args or []

    # The desktop tool prints a Unicode banner; force UTF-8 so it doesn't crash
    # on Windows consoles that default to cp1252.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

    print(f"Running: {' '.join(cmd)}\n(working dir: {workdir})\n")
    try:
        return subprocess.call(cmd, cwd=str(desktop), env=env)
    finally:
        if export_pdf:
            _collect_pdfs(workdir, order_xml.parent)


def _collect_pdfs(workdir: Path, dest: Path) -> None:
    for pdf in workdir.glob("*.pdf"):
        target = dest / pdf.name
        shutil.copy2(pdf, target)
        print(f"PDF proof written to: {target}")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _self_command() -> list[str]:
    """How to re-invoke this app's CLI (frozen exe vs. python -m)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "lotrautofill"]


def launch_autofill_terminal(order_xml: Path, browser: str = "chrome",
                             export_pdf: bool = False) -> str:
    """Launch `autofill <order_xml>` in a NEW console window.

    The desktop tool has an interactive console UI (login, review, or the PDF
    layout questions) and must run in a real terminal — so the web GUI spawns it
    in its own window rather than capturing it. Returns a status message.
    """
    order_xml = Path(order_xml).resolve()
    cmd = _self_command() + ["autofill", str(order_xml), "--browser", browser]
    if export_pdf:
        cmd.append("--pdf")

    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(cmd, creationflags=creationflags, close_fds=True)
        return "Launched the MPC autofill tool in a new console window."

    for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
        if shutil.which(term):
            flag = "--" if term == "gnome-terminal" else "-e"
            try:
                subprocess.Popen([term, flag, *cmd])
                return f"Launched the MPC autofill tool in {term}."
            except OSError:
                continue
    # No terminal emulator found — run detached (interactive UI may not attach).
    subprocess.Popen(cmd)
    return ("Started the MPC autofill tool (no terminal emulator found — run "
            f"it manually if needed: {' '.join(cmd)}).")
