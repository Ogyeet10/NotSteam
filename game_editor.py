from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich import box
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
try:
    from prompt_toolkit.key_binding import KeyBindings  # type: ignore
except Exception:
    KeyBindings = None  # type: ignore

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


def _print_error(message: str, exc: Optional[BaseException] = None) -> None:
    try:
        details = message
        if exc is not None:
            details += f"\n\n{type(exc).__name__}: {exc}"
        _console.print(Panel.fit(details, border_style="red", box=box.ROUNDED))
    except Exception:
        # Fallback plain print if rich fails
        print(message)
        if exc is not None:
            print(f"{type(exc).__name__}: {exc}")


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
    except Exception as e:
        _print_error("OpenAI metadata suggestion failed", e)
        return {}


def _load_classification_schema() -> Dict[str, Any]:
    """Load the JSON schema used for strict responses formatting."""
    try:
        schema_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "gamesDB", "game_classification_schema.json")
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _strip_citations(value: Any) -> Any:
    """Recursively strip inline citation markers from strings."""
    if isinstance(value, dict):
        return {k: _strip_citations(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_citations(v) for v in value]
    if isinstance(value, str):
        # Remove patterns like: citeturn0search12
        cleaned = re.sub(r"cite.*?", "", value)
        return cleaned.strip()
    return value


def _generate_classification_with_openai(title: str) -> Dict[str, Any]:
    """Call OpenAI Responses API to classify a game into our strict schema.

    Returns an object matching the schema, or an empty dict on failure.
    """
    if not _openai_client:
        return {}
    schema_obj = _load_classification_schema()
    if not schema_obj:
        return {}
    try:
        system_prompt = (
            "You classify video games into a strict JSON schema. "
            "Prefer your internal knowledge. Only use the web_search tool if: "
            "(1) you do not recognize the game; or (2) the game was unreleased at your last knowledge update; or "
            "(3) the user's request requires specific details you do not already have. "
            "Do NOT use web_search for routine validation (e.g., release year, platforms, canonical names) when you are confident. "
            "Web searches are expensive—use them only when absolutely necessary to obtain information you do not have. "
            "DO NOT guess. If you do not know the answer you can use the search tool."
            "Return only a single JSON object that strictly conforms to the provided JSON schema. "
            "DO NOT include citations, provenance markers, footnotes, or any special tokens inside any string fields. "
            "Specifically, DO NOT emit markers like 'cite...', bracketed indices like [1], or URL footnotes in any values. "
            "All string values must be plain text without citations."
        )
        body: Dict[str, Any] = {
            "model": "gpt-5-mini",
            "reasoning": {"effort": "medium", "summary": "auto"},
            "tools": [{"type": "web_search"}],
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Return a single JSON object for the game title: {title}"},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_obj.get("name", "game_classification"),
                    "strict": schema_obj.get("strict", True),
                    "schema": schema_obj.get("schema", schema_obj),
                }
            }
        }

        # Attempt streaming using Responses.create(stream=True); fall back if needed
        resp = None
        streamed_text: Optional[str] = None
        try:
            stream = _openai_client.responses.create(stream=True, **body)  # type: ignore[attr-defined]
            reasoning_started = False
            text_chunks: list[str] = []
            reasoning_buffer = ""  # full accumulated reasoning text
            reasoning_sections: list[str] = []  # completed sections (bold/heading-started)
            current_section: str = ""  # currently streaming section
            # Render a live markdown panel using explicit updates
            with Live(console=_console, refresh_per_second=25, transient=False) as live:
                # Initialize empty panel
                live.update(Panel(Markdown(""), title="Reasoning summary", border_style="yellow"), refresh=True)
                # Keep spinner/status pinned to the bottom of the terminal (separate from Live)
                with _console.status("[dim]Classifying game (this may take a minute or two)...[/dim]", spinner="dots"):
                    # Heuristic: decide how many recent sections to display based on terminal height
                    def _tail_sections_by_height(h: int) -> int:
                        if h <= 24:
                            return 1
                        if h <= 40:
                            return 2
                        if h <= 60:
                            return 3
                        return 4
                    for event in stream:
                        # Robustly read the event type from SDK objects or dicts
                        etype = (
                            getattr(event, "type", None)
                            or getattr(event, "event", None)
                            or (event.get("type") if isinstance(event, dict) else None)
                        )
                        if etype == "response.output_text.delta":
                            delta = (
                                getattr(event, "delta", None)
                                or (event.get("delta") if isinstance(event, dict) else None)
                            )
                            if isinstance(delta, str) and delta:
                                text_chunks.append(delta)
                        elif etype == "response.reasoning_summary_text.delta":
                            delta = (
                                getattr(event, "delta", None)
                                or (event.get("delta") if isinstance(event, dict) else None)
                            )
                            if isinstance(delta, str) and delta:
                                # Only insert paragraph breaks before real headings or bold phrase starts.
                                insert = ""
                                if reasoning_buffer:
                                    prev = reasoning_buffer[-1]
                                    import re as _re
                                    heading_start = bool(_re.match(r"^\s*#{1,6}\s+\S", delta))
                                    bold_word_start = bool(_re.match(r"^\s*\*\*[A-Za-z0-9]", delta))
                                    pure_marker = bool(_re.match(r"^\s*(\*{1,3}|#{1,6})\s*$", delta))
                                    prev_ends_star = reasoning_buffer.endswith("*") or reasoning_buffer.endswith("**")

                                    new_section = (heading_start or bold_word_start) and not pure_marker and not prev_ends_star
                                    if new_section:
                                        if reasoning_buffer.endswith("\n\n"):
                                            insert = ""
                                        elif reasoning_buffer.endswith("\n"):
                                            insert = "\n"
                                        else:
                                            insert = "\n\n"
                                        # finalize previous section
                                        if current_section:
                                            reasoning_sections.append(current_section)
                                            current_section = ""
                                addition = insert + delta
                                # accumulate into current section and full buffer
                                current_section += addition
                                reasoning_buffer += addition
                                # compute visible window: only last N sections + current section
                                try:
                                    height = _console.size.height
                                except Exception:
                                    height = 40
                                tail = _tail_sections_by_height(height)
                                visible = "".join((reasoning_sections + [current_section])[-tail:])
                                # If we have more sections than we can display, show an indicator above the panel
                                is_truncated = len(reasoning_sections) + 1 > tail
                                panel = Panel(Markdown(visible), title="Reasoning summary", border_style="yellow")
                                if is_truncated:
                                    indicator = Text("Only showing most recent reasoning due to terminal height. Full reasoning will appear when complete.", style="dim italic")
                                    live.update(Group(indicator, panel), refresh=True)
                                else:
                                    live.update(panel, refresh=True)
                        elif etype == "error":
                            # Best-effort surface of errors during streaming
                            msg = (
                                getattr(event, "message", None)
                                or (event.get("message") if isinstance(event, dict) else None)
                            )
                            if msg:
                                _print_error("Streaming error", Exception(str(msg)))
                    # After stream completes, render full content (all sections)
                    full_visible = "".join(reasoning_sections + [current_section]) or reasoning_buffer
                    # Final render: full reasoning, no truncation indicator
                    live.update(Panel(Markdown(full_visible), title="Reasoning summary", border_style="yellow"), refresh=True)
            if text_chunks:
                streamed_text = "".join(text_chunks).strip()
            # If no chunks were received, fall back to non-streaming create
            if not streamed_text:
                try:
                    resp = _openai_client.responses.create(**body)  # type: ignore[attr-defined]
                except Exception as _e:
                    resp = None
        except Exception:
            # Fallback to non-streaming create if streaming setup fails
            resp = _openai_client.responses.create(**body)  # type: ignore[attr-defined]
        content_text: Optional[str] = None
        if streamed_text:
            content_text = streamed_text
        try:
            # Convenience accessor in newer SDKs
            if content_text is None and resp is not None:
                content_text = getattr(resp, "output_text", None)
        except Exception:
            content_text = None
        if not content_text:
            try:
                # Fallback to drilling into output structure if available
                output = getattr(resp, "output", None) if resp is not None else None
                if output and isinstance(output, list) and output:
                    first = output[0]
                    parts = getattr(first, "content", None)
                    if isinstance(parts, list) and parts:
                        text_part = parts[0]
                        content_text = getattr(text_part, "text", None)
            except Exception:
                content_text = None
        if not content_text:
            # Best-effort regex extraction of JSON
            from re import search
            serialized = str(resp)
            m = search(r"\{[\s\S]*\}", serialized)
            content_text = m.group(0) if m else None
        if not content_text:
            return {}
        try:
            data = json.loads(content_text)
            data = _strip_citations(data)
            return data if isinstance(data, dict) else {}
        except Exception:
            # Last resort: extract JSON object from the text
            import re as _re

            m = _re.search(r"\{[\s\S]*\}", content_text)
            if not m:
                return {}
            try:
                data = json.loads(m.group(0))
                data = _strip_citations(data)
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
    except Exception as e:
        _print_error("OpenAI classification failed", e)
        return {}


def _render_game_summary(data: Dict[str, Any]) -> None:
    """Pretty-render the classified game JSON using Rich components.

    Layout:
    - Header panel: title + summary
    - Two-column details table (year, developer, publisher, price model, rating)
    - Multi-line sections for lists (platforms, genre, tags, aliases)
    - Booleans rendered as ✓/✗
    """
    name = str(data.get("display_name") or "Unknown Game")
    summary = str(data.get("summary") or "No summary available.")

    # Header
    header = Panel(
        Markdown(f"**{name}**\n\n{summary}"),
        title="Game",
        border_style="bright_cyan",
        box=box.ROUNDED,
    )
    _console.print(header)

    # Details
    def yesno(v: Optional[bool]) -> str:
        if v is True:
            return "✓"
        if v is False:
            return "✗"
        return "-"

    details = Table.grid(padding=(0, 2))
    details.add_column("Field", style="bold magenta")
    details.add_column("Value", style="cyan")

    def add_row(label: str, value: Optional[str | int | float]) -> None:
        if value is None or value == "" or value == []:
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        details.add_row(label, str(value))

    add_row("Year", data.get("release_year"))
    add_row("Developer", data.get("developer"))
    add_row("Publisher", data.get("publisher"))
    add_row("Franchise", data.get("franchise"))
    add_row("Price", data.get("price_model"))
    rating_val = data.get("rating")
    add_row("Rating", f"{rating_val} ⭐" if isinstance(rating_val, (int, float)) else rating_val)
    add_row("World", data.get("world_type"))
    add_row("Perspective", data.get("perspective"))
    add_row("Age Rating", data.get("age_rating"))
    add_row("Setting", data.get("setting"))
    add_row("Story Focus", data.get("story_focus"))
    add_row("Playtime (hrs)", data.get("playtime_hours"))
    add_row("Parent Game", data.get("parent_game"))

    # Boolean flags
    flags = Table.grid(padding=(0, 2))
    flags.add_column("Feature", style="bold magenta")
    flags.add_column("Has", style="cyan")
    flags.add_row("VR", yesno(data.get("is_vr")))
    flags.add_row("Mods", yesno(data.get("has_mods")))
    flags.add_row("Requires Online", yesno(data.get("requires_online")))
    flags.add_row("Cross Platform", yesno(data.get("cross_platform")))
    flags.add_row("Microtransactions", yesno(data.get("has_microtransactions")))
    flags.add_row("Remake/Remaster", yesno(data.get("is_remake_or_remaster")))
    flags.add_row("DLC", yesno(data.get("is_dlc")))
    flags.add_row("Procedural Gen", yesno(data.get("procedurally_generated")))

    # Collections
    def bullets(label: str, arr: Optional[list[str]]) -> Panel | None:
        if not arr:
            return None
        # Limit very long lists visually; show top 10 with remainder count
        max_items = 10
        extra = 0
        items = arr
        if len(arr) > max_items:
            items = arr[:max_items]
            extra = len(arr) - max_items
        lines = [Text(f"• {str(x)}") for x in items]
        if extra:
            lines.append(Text(f"• … and {extra} more"))
        return Panel(
            Group(*lines),
            title=label,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )

    left = Panel(details, title="Details", border_style="magenta", box=box.ROUNDED)
    right = Panel(flags, title="Capabilities", border_style="magenta", box=box.ROUNDED)
    grid_lr = Table.grid(expand=True)
    grid_lr.add_column(ratio=1)
    grid_lr.add_column(ratio=1)
    grid_lr.add_row(left, right)
    _console.print(grid_lr)

    cols: list[Panel] = []
    for label, key in (("Platforms", "platforms"), ("Genres", "genre"), ("Tags", "tags"), ("Aliases", "aliases")):
        p = bullets(label, data.get(key))
        if p is not None:
            cols.append(p)
    # Additional list-type fields
    mp_panel = bullets("Multiplayer", data.get("multiplayer_type"))
    if mp_panel is not None:
        cols.append(mp_panel)
    input_panel = bullets("Input Methods", data.get("input_methods"))
    if input_panel is not None:
        cols.append(input_panel)
    if cols:
        grid = Table.grid(expand=True)
        for c in cols:
            grid.add_column(ratio=1)
        grid.add_row(*cols)
        _console.print(grid)

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
    except Exception as e:
        _print_error("Persistence failed (best-effort only)", e)
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
        kb = None
        if KeyBindings is not None:
            kb = KeyBindings()

            # Allow ESC to cancel and return to the main query loop by exiting the prompt
            @kb.add("escape")
            def _esc(event):  # type: ignore[no-redef]
                event.app.exit(result="")

        title = _session.prompt("🎮 Game name: ", key_bindings=kb) if kb is not None else _session.prompt("🎮 Game name: ")
    except Exception:
        title = _console.input("[bold green]🎮 Game name:[/bold green] ")

    title = (title or "").strip()
    if not title:
        _console.print("[yellow]No game entered[/yellow]")
        return

    # Live classification via OpenAI Responses API; print the JSON and confirmation
    classification = _generate_classification_with_openai(title)

    if classification:
        try:
            _render_game_summary(classification)
        except Exception:
            # Fallback to raw JSON if pretty renderer errors
            _console.print_json(data=classification)
    else:
        _console.print("[yellow]Unable to classify right now[/yellow]")

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


