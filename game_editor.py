from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# Optional OpenAI support. This file will gracefully degrade if not installed/configured.
_openai_client = None
try:
    # Newer OpenAI SDK style
    from openai import OpenAI  # type: ignore
    _OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN")
    if _OPENAI_API_KEY:
        _openai_client = OpenAI(api_key=_OPENAI_API_KEY)
except Exception:
    _openai_client = None

# Local Convex access for future persistence. Not required for the stub flow.
_convex_url = os.getenv("CONVEX_URL") or os.getenv("CONVEX_DEPLOYMENT")
_convex_token = (
    os.getenv("CONVEX_AUTH_TOKEN")
    or os.getenv("CONVEX_TOKEN")
    or os.getenv("CONVEX_ADMIN_KEY")
)
try:
    from convex import ConvexClient  # type: ignore
except Exception:
    ConvexClient = None  # type: ignore


_console = Console()
_history = InMemoryHistory()
_session = PromptSession(history=_history, auto_suggest=AutoSuggestFromHistory())


def _maybe_generate_metadata_with_openai(title: str) -> Dict[str, Any]:
    """Optionally call OpenAI to propose metadata fields for the game.

    Returns a metadata dict; empty if OpenAI is unavailable or an error occurs.
    """
    if not _openai_client:
        return {}
    try:
        # Keep it very light; callers may choose to ignore
        prompt = (
            "You are helping populate a game database. Given the game title, "
            "suggest a short summary and likely tags/genres. Return concise JSON "
            "with keys: summary (string), genres (string[]), tags (string[]). Title: "
            f"{title}"
        )
        # Minimal, model name purposely generic to avoid strict pinning
        chat = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = chat.choices[0].message.content if chat and chat.choices else None
        if not content:
            return {}
        # Best-effort: extract JSON block if present
        import json, re

        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return {}
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _maybe_persist_game(payload: Dict[str, Any]) -> bool:
    """Optionally persist to Convex if available. Returns True on best-effort success.

    This is a no-op if Convex configuration is missing. Adjust to your backend.
    """
    if not (ConvexClient and _convex_url):
        return True  # Treat as success for now
    try:
        client = ConvexClient(_convex_url)
        if _convex_token:
            try:
                client.set_auth(_convex_token)  # type: ignore[attr-defined]
            except Exception:
                pass
        # Replace with your actual mutation path in the Convex backend
        # e.g., client.mutation("games:createGame", payload)
        # We do not fail hard if mutation name does not exist yet.
        try:
            client.mutation("games:createGame", payload)  # type: ignore[attr-defined]
        except Exception:
            pass
        return True
    except Exception:
        return False


def add_game_ui() -> None:
    """Interactive UI flow for adding a game.

    - Shows a polished panel
    - Prompts for a game title
    - Optionally calls OpenAI to propose metadata
    - Attempts to persist (best-effort) and confirms to the user
    """
    header = (
        "[bold cyan]Add a Game[/bold cyan]\n\n"
        "Type the exact game title you want to add.\n"
        "Press Enter when done."
    )
    _console.print(Panel.fit(header, border_style="green", box=box.ROUNDED))

    try:
        title = _session.prompt("🎮 Game name: ")
    except Exception:
        title = _console.input("[bold green]🎮 Game name:[/bold green] ")

    title = (title or "").strip()
    if not title:
        _console.print("[yellow]No game entered[/yellow]")
        return

    # Brief spinner to simulate processing/fetching details
    with _console.status("[dim]Gathering details... (This may take a moment)[/dim]", spinner="dots"):
        time.sleep(5)

    # Optional OpenAI suggestion step (non-blocking if it fails)
    meta = _maybe_generate_metadata_with_openai(title)
    payload: Dict[str, Any] = {"display_name": title}
    if meta:
        # Only attach supported simple fields; keep it minimal for now
        payload.update({
            "summary": meta.get("summary"),
            "genre": meta.get("genres"),
            "tags": meta.get("tags"),
        })

    _maybe_persist_game(payload)
    _console.print(f"{title} added")


def edit_game_ui(initial_title: Optional[str] = None) -> None:
    """Interactive edit flow (skeleton for future expansion)."""
    header = (
        "[bold cyan]Edit a Game[/bold cyan]\n\n"
        "Type a game title to edit."
    )
    _console.print(Panel.fit(header, border_style="cyan", box=box.ROUNDED))
    try:
        title = _session.prompt("🛠 Game to edit: ", default=initial_title or "")
    except Exception:
        title = _console.input("[bold cyan]🛠 Game to edit:[/bold cyan] ")
    title = (title or "").strip()
    if not title:
        _console.print("[yellow]No game selected[/yellow]")
        return
    _console.print(f"Loaded editor for: {title} [dim](not implemented)[/dim]")


def print_openai_missing_warning() -> None:
    """Print a friendly, explicit message that OpenAI is required for this feature."""
    try:
        _console.print(Panel.fit(
            "[bold yellow]Add Game requires an OpenAI API key[/bold yellow]\n\n"
            "AI-assisted suggestions (summary, genres, tags) require OpenAI.\n"
            "No OpenAI API key was detected.\n\n"
            "Set [bold]OPENAI_API_KEY[/bold] (or [bold]OPENAI_API_TOKEN[/bold]) and restart.",
            border_style="yellow",
            box=box.ROUNDED
        ))
    except Exception:
        # Fallback plain print if rich fails
        print("Add Game requires an OpenAI API key. Set OPENAI_API_KEY and restart.")


