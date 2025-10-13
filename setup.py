#!/usr/bin/env python3
"""
Repo bootstrapper for Windows environments using Astral's uv.

Behavior:
- Validate Windows OS.
- Ensure `uv` is installed (install via Astral's install script if missing, with console passthrough).
- Ensure a project virtual environment exists and dependencies are synced via `uv sync`.

Notes:
- Uses only the Python standard library.
- Attempts to make installer output visible to the user.
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Union
from glob import glob


def enable_windows_ansi_colors() -> None:
    """Enable ANSI escape sequences in Windows terminals when possible."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes  # stdlib

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        # Best effort only; safe to ignore.
        pass


class Style:
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    if os.name == "nt":
        # After enabling ANSI, Windows 10+ supports colors; if not, fall back to plain text
        return f"{color}{text}{Style.RESET}"
    return f"{color}{text}{Style.RESET}"


def banner(title: str) -> None:
    line = "=" * max(38, len(title) + 8)
    print(colorize(line, Style.CYAN))
    print(colorize(f"  {title}  ", Style.BOLD))
    print(colorize(line, Style.CYAN))


def step(msg: str) -> None:
    print(colorize(f"→ {msg}", Style.CYAN))


def success(msg: str) -> None:
    print(colorize(f"✔ {msg}", Style.GREEN))


def warn(msg: str) -> None:
    print(colorize(f"! {msg}", Style.YELLOW))


def error(msg: str) -> None:
    print(colorize(f"✖ {msg}", Style.RED))


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


# Tracks the best-known invocation for uv, e.g. 'uv' or a full path to uv.exe
UV_CMD = ["uv"]
UV_JUST_INSTALLED = False


def run_passthrough(cmd: Union[str, Iterable[str]], check: bool = False) -> int:
    """Run a command inheriting the parent's stdio so UI/output is visible.

    Tries without shell first; if not found, retries with shell=True on Windows.
    Returns the process return code.
    """
    try:
        result = subprocess.run(cmd, check=check)
        return result.returncode
    except FileNotFoundError:
        # Retry with shell on Windows to leverage PATH resolution from the shell
        if platform.system() == "Windows":
            if isinstance(cmd, (list, tuple)):
                cmd = " ".join(map(str, cmd))
            result = subprocess.run(cmd, shell=True, check=False)
            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd)
            return result.returncode
        return 127


def check_python_version(min_major: int = 3, min_minor: int = 9) -> None:
    py_ver = sys.version_info
    if (py_ver.major, py_ver.minor) < (min_major, min_minor):
        warn(
            f"Python {min_major}.{min_minor}+ is recommended, detected {py_ver.major}.{py_ver.minor}."
        )


def ensure_winget_available() -> bool:
    # No longer required; retained for backward compatibility.
    return False


def ensure_uv_available() -> bool:
    global UV_CMD
    if command_exists("uv"):
        success("`uv` is already installed.")
        return True

    system = platform.system()

    if system == "Windows":
        step("`uv` not found. Installing via Astral's install script…")
        # Install using PowerShell script recommended by Astral
        install_cmd = [
            "powershell",
            "-ExecutionPolicy",
            "ByPass",
            "-c",
            "irm https://astral.sh/uv/install.ps1 | iex",
        ]

        rc = run_passthrough(install_cmd, check=False)
        if rc != 0:
            error("Failed to install uv via install script (see output above).")
            return False

        # Mark that we installed uv in this run to inform the user about VS Code restart
        global UV_JUST_INSTALLED
        UV_JUST_INSTALLED = True

        # Attempt to refresh PATH in this process so newly added locations are visible
        refresh_process_env_path()

        # Re-check PATH for uv
        if command_exists("uv"):
            success("`uv` installed and detected on PATH.")
            return True

        # Try again via shell in case PATH updates are pending in this session
        rc = run_passthrough(["uv", "--version"], check=False)
        if rc == 0:
            success("`uv` is available.")
            return True

        # Fallback: try to locate uv.exe in common install locations and use absolute path
        uv_path = try_locate_uv_executable()
        if uv_path:
            UV_CMD = [str(uv_path)]
            warn(
                f"Using uv at: {uv_path} (PATH may require a new terminal to update)."
            )
            return True

        warn(
            "`uv` installation succeeded but not detected in this shell session. Try opening a new terminal if subsequent steps fail."
        )
        return command_exists("uv")

    # Non-Windows (macOS/Linux): install via curl | sh
    step("`uv` not found. Installing via Astral's install script (curl | sh)…")
    if system == "Linux" and not command_exists("curl"):
        error("`curl` is required to install uv. Please install curl and re-run this script.")
        return False

    rc = run_passthrough(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"], check=False)
    if rc != 0:
        error("Failed to install uv via install script (see output above).")
        return False

    # After install, uv is typically placed under ~/.local/bin; PATH may already include it
    if command_exists("uv"):
        success("`uv` installed and detected on PATH.")
        return True

    # Try common install location on Unix
    uv_unix = Path.home() / ".local" / "bin" / "uv"
    if uv_unix.exists():
        UV_CMD = [str(uv_unix)]
        warn(f"Using uv at: {uv_unix} (ensure ~/.local/bin is on your PATH).")
        return True

    warn("`uv` installation completed but not detected on PATH in this session. Open a new terminal or ensure ~/.local/bin is in PATH.")
    return command_exists("uv")


def ensure_project_env_synced() -> bool:
    root = repo_root()
    venv_dir = root / ".venv"

    if venv_dir.exists():
        success("Existing .venv detected. Ensuring dependencies are in sync…")
    else:
        step("No .venv found. Creating environment and installing dependencies with `uv sync`…")

    # Prefer `uv sync` since this project includes `uv.lock`/`pyproject.toml`
    rc = run_passthrough([*UV_CMD, "sync"], check=False)
    if rc != 0:
        error("`uv sync` failed (see output above).")
        return False

    if not venv_dir.exists():
        # `uv sync` should create .venv by default; if not, fall back to explicit venv creation
        warn("`.venv` not found after sync. Creating venv explicitly and syncing again…")
        rc_venv = run_passthrough([*UV_CMD, "venv"], check=False)
        if rc_venv != 0:
            error("`uv venv` failed to create a virtual environment.")
            return False
        rc_sync = run_passthrough([*UV_CMD, "sync"], check=False)
        if rc_sync != 0:
            error("`uv sync` failed after creating venv.")
            return False

    success("Environment is ready.")
    return True


def refresh_process_env_path() -> None:
    """Refresh PATH in the current process from registry values (Windows only).

    This makes newly added installer paths visible without restarting PowerShell.
    Also ensures the WinGet Links directory is included for newly created aliases.
    """
    if platform.system() != "Windows":
        return
    try:
        # Read Machine and User PATH from registry and combine.
        import winreg  # type: ignore

        parts = []
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "Path")
                if val:
                    parts.append(val)
        except Exception:
            pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                val, _ = winreg.QueryValueEx(key, "Path")
                if val:
                    parts.append(val)
        except Exception:
            pass

        combined = ";".join([p for p in parts if p])
        if combined:
            os.environ["PATH"] = combined
    except Exception:
        # Best effort only.
        pass

    # Ensure WinGet Links directory is present in the process PATH for aliases like uv/uvx
    links = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"))
    if links.exists():
        current = os.environ.get("PATH", "")
        if str(links) not in current:
            os.environ["PATH"] = f"{str(links)};{current}" if current else str(links)

    # Ensure Astral's default install location is present in the process PATH
    local_bin = Path(os.path.expandvars(r"%USERPROFILE%\.local\bin"))
    if local_bin.exists():
        current = os.environ.get("PATH", "")
        if str(local_bin) not in current:
            os.environ["PATH"] = f"{str(local_bin)};{current}" if current else str(local_bin)


def try_locate_uv_executable() -> Union[Path, None]:
    """Search common install locations for uv.exe as a fallback."""
    if platform.system() != "Windows":
        return None
    candidates: list[Path] = []
    # WinGet links (legacy path if previously installed via winget)
    links_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"))
    if links_dir.exists():
        for pattern in ("uv.exe", "uvx.exe"):
            for match in links_dir.glob(pattern):
                candidates.append(match)
    # Astral install script default location
    local_bin = Path(os.path.expandvars(r"%USERPROFILE%\.local\bin"))
    if local_bin.exists():
        for pattern in ("uv.exe", "uvx.exe"):
            for match in local_bin.glob(pattern):
                candidates.append(match)
    return candidates[0] if candidates else None


def ensure_dotenv_created() -> bool:
    """Create or update a .env file with required starter contents."""
    env_path = repo_root() / ".env"
    desired = "CONVEX_URL=https://unique-condor-115.convex.cloud\n"
    try:
        if env_path.exists():
            try:
                current = env_path.read_text(encoding="utf-8")
            except Exception:
                current = ""
            if current.strip() == desired.strip():
                success(".env already exists with required contents.")
                return True
            warn("Updating existing .env with required contents…")
        else:
            step("Creating .env with starter contents…")
        env_path.write_text(desired, encoding="utf-8")
        success(f"Wrote {env_path.name}.")
        return True
    except Exception as exc:
        error(f"Failed to write .env: {exc}")
        return False


def main() -> int:
    enable_windows_ansi_colors()
    banner("NotSteam Repo Setup")
    check_python_version()
    # Ensure we execute from the repository root so `uv` finds the right files
    try:
        os.chdir(repo_root())
    except Exception:
        pass

    step("Checking for `uv`…")
    if not ensure_uv_available():
        return 1

    step("Preparing project virtual environment…")
    if not ensure_project_env_synced():
        return 1

    root = repo_root()
    # Create/update .env with required Convex URL
    ensure_dotenv_created()
    print()
    if platform.system() == "Windows" and UV_JUST_INSTALLED:
        warn(
            "In VS Code, the `uv` command WILL NOT be available in the integrated terminal until you RESTART VSCode."
        )
    success("Setup complete!")
    act_path = (
        root / ".venv" / "Scripts" / "activate"
        if platform.system() == "Windows"
        else root / ".venv" / "bin" / "activate"
    )
    print(f"Activate your environment with: {colorize(str(act_path), Style.BOLD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


