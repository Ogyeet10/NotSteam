from match import match
import os
from typing import List, Tuple, Callable, Any
from gamesDB import api as games_api
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
try:
    from prompt_toolkit.application.current import get_app_or_none  # type: ignore
except Exception:
    get_app_or_none = None  # type: ignore

console = Console()
VERSION = "1.2.1"

# Track the last game the user interacted with for quick edits
_last_selected_game: dict | None = None
def _bottom_toolbar() -> HTML:
    """Bottom toolbar for main prompt and pick prompts.

    Left: NotSteam + version, Center: Enter/send, Right: Ctrl-C/exit.
    """
    try:
        cols = 80
        if get_app_or_none is not None:
            app = get_app_or_none()
            if app is not None:
                try:
                    size = app.output.get_size()
                    cols = getattr(size, "columns", cols) or cols
                except Exception:
                    pass

        brand_plain = f"NotSteam v{VERSION}"
        center_plain = "Enter send"
        right_plain = "Ctrl-C exit"

        start_center = max((cols - len(center_plain)) // 2, len(brand_plain) + 1)
        RIGHT_MARGIN = 1
        start_right = max(cols - len(right_plain) - RIGHT_MARGIN, start_center + len(center_plain) + 1)
        pad_center = max(start_center - len(brand_plain), 1)
        pad_right = max(start_right - (start_center + len(center_plain)), 1)

        left = f'<b><style bg="#FFFFFF">NotSteam</style></b> v{VERSION}'
        center = '<b><style bg="#FFFFFF">Enter</style></b> send'
        right = '<b><style bg="#FFFFFF">Ctrl^C</style></b> exit'
        line = " " + left + (" " * pad_center) + center + (" " * pad_right) + right
        return HTML(f'<style bg="#606060" fg="#242424">{line}</style>')
    except Exception:
        return HTML(f'<style bg="#606060" fg="#242424"><b><style bg="#0b5fff">NotSteam</style></b> v{VERSION} | Enter: send | Ctrl-C: exit</style>')


# Helper to normalize Convex paginated vs list responses
def _extract_docs(page_or_list: Any) -> List[dict]:
    if isinstance(page_or_list, dict):
        return page_or_list.get("page") or []
    if isinstance(page_or_list, list):
        return page_or_list
    return []

# Helpers for rendering

def _render_game_list(games: List[dict], title: str = "Games") -> None:
    if not games:
        console.print("[yellow]No games found[/yellow]")
        return
    table = Table(title=title, box=box.ROUNDED, show_header=False)
    table.add_column("Game", style="cyan")
    for g in games:
        table.add_row(g.get('display_name', '?'))
    console.print(table)

def _names_list(games: List[dict]) -> List[str]:
    return [f"- {g.get('display_name', '?')}" for g in games]

def _bullets(items: List[str]) -> List[str]:
    return [f"- {i}" for i in items]

def _render_pick_list(candidates: List[dict]) -> None:
    table = Table(title="Which did you mean?", box=box.ROUNDED, show_header=True)
    table.add_column("#", style="magenta", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Year", style="green", no_wrap=True)
    for idx, g in enumerate(candidates, start=1):
        name = g.get("display_name", "?")
        year = g.get("release_year")
        year_str = str(int(year)) if isinstance(year, (int, float)) else (str(year) if year is not None else "-")
        table.add_row(str(idx), name, year_str)
    console.print(table)

def _prompt_pick_index(max_index: int) -> int:
    while True:
        try:
            raw = _session.prompt(f"Pick 1-{max_index} (or 0 to cancel): ", bottom_toolbar=_bottom_toolbar)
        except Exception:
            raw = console.input(f"Pick 1-{max_index} (or 0 to cancel): ")
        raw = (raw or "").strip()
        if raw.isdigit():
            i = int(raw)
            if 0 <= i <= max_index:
                return i
        console.print("[yellow]Invalid selection[/yellow]")

def resolve_game_interactively(name: str, limit: int = 10) -> dict | None:
    global _last_selected_game
    # Exact by normalized_name first
    g = games_api.get_game_by_name(name)
    if g:
        _last_selected_game = g
        return g
    # Otherwise show top matches and let user choose
    hits = games_api.search_games_by_name(name, limit=limit)
    if not hits:
        return None
    if len(hits) == 1:
        _last_selected_game = hits[0]
        return hits[0]
    _render_pick_list(hits)
    pick = _prompt_pick_index(len(hits))
    if pick == 0:
        return None
    sel = hits[pick - 1]
    _last_selected_game = sel
    return sel

def _singularize_tag(tag: str) -> str:
    t = tag.strip().lower()
    if t.endswith("ies") and len(t) > 3:
        return t[:-3] + "y"
    if t.endswith("es") and len(t) > 2:
        return t[:-2]
    if t.endswith("s") and len(t) > 1:
        return t[:-1]
    return t

def _normalize_tag_candidates(tag: str) -> List[str]:
    t = tag.strip().lower()
    # Common synonyms, hyphen/space preferences, and misspellings
    synonyms = {
        "rougelike": "roguelike",
        "rougelite": "roguelite",
        "souls like": "soulslike",
        "twin stick": "twin-stick",
        "bullet hell": "bullet-hell",
        "deck builder": "deckbuilder",
        "deck building": "deckbuilder",
        "deck-building": "deckbuilder",
        "open world": "open-world",
        "sci fi": "sci-fi",
        "scifi": "sci-fi",
        "turn based": "turn-based",
        "tbs": "turn-based",
    }
    base = synonyms.get(t, t)

    variants: List[str] = []
    def add(v: str) -> None:
        if v and v not in variants:
            variants.append(v)

    add(base)
    singular = _singularize_tag(base)
    add(singular)

    # Hyphen/space variations
    add(base.replace(" ", "-"))
    add(base.replace("-", " "))
    add(singular.replace(" ", "-"))
    add(singular.replace("-", " "))

    # Joined form (e.g., "rogue lite" -> "roguelite")
    add(base.replace(" ", ""))
    add(singular.replace(" ", ""))

    return [v for v in variants if v]

def _normalize_franchise_candidates(q: str) -> List[str]:
    t = (q or "").strip()
    if not t:
        return []
    low = t.lower()
    # Minimal, high-signal franchise synonyms/aliases
    synonyms: dict[str, str] = {
        "gta": "grand theft auto",
        "cod": "call of duty",
        "ff": "final fantasy",
        "zelda": "the legend of zelda",
        "nfs": "need for speed",
        "mk": "mortal kombat",
        "assassins creed": "assassin's creed",
        "assassin creed": "assassin's creed",
    }
    base = synonyms.get(low, t)
    candidates: List[str] = []
    def add(v: str) -> None:
        if v and v not in candidates:
            candidates.append(v)
    add(base)
    # Also try title-cased form which often matches stored franchise naming
    add(base.title())
    return candidates

def _parse_limit(matches: List[str], default: int = 25) -> int:
    for token in matches:
        tok = token.strip()
        if tok.isdigit():
            try:
                val = int(tok)
                if val > 0:
                    return val
            except Exception:
                pass
    return default

# Prompt session with history
_history = InMemoryHistory()
_session = PromptSession(history=_history, auto_suggest=AutoSuggestFromHistory())
_completer = WordCompleter([
    'what', 'when', 'who', 'show', 'show me', 'is',
    'what games were made in', 'what games were made between',
    'what games were made before', 'what games were made after',
    'who made', 'what games were made by', 'when was',
    'describe', 'what is', 'what is about', 'what platforms is',
    'what genres is', 'what genre is', 'what tags does', 'show vr games',
    'show online games', 'show free to play games', 'show paid games',
    'help', 'commands', 'how do i use this', '?',
    # Common tags & genres (plus a few misspellings)
    'roguelike', 'rougelike', 'roguelite', 'rougelite', 'rogue-like', 'rogue lite',
    'soulslike', 'souls like', 'metroidvania', 'metroidvanias',
    'fps', 'shooter', 'twin-stick', 'bullet hell',
    'rpg', 'jrpg', 'arpg', 'mmorpg',
    'strategy', 'rts', 'tbs', '4x',
    'puzzle', 'platformer', 'platformers',
    'sandbox', 'open world', 'survival', 'horror',
    'sci-fi', 'scifi', 'fantasy', 'cyberpunk', 'steampunk',
    'deckbuilder', 'card game', 'card games',
    'moba', 'battle royale', 'stealth', 'rhythm',
    'racing', 'sports', 'simulation', 'management',
    'city builder', 'farming', 'crafting', 'building', 'exploration',
    'narrative', 'visual novel', 'point and click', 'indie',
    'multiplayer', 'singleplayer', 'co-op', 'coop', 'local co-op', 'online co-op',
    'pvp', 'pve', 'vr', 'online', 'free to play', 'paid',
    'franchise', 'series', 'add a game', 'add game', 'create game', 'new game'
], ignore_case=True)

# Action functions must be defined BEFORE pa_list
def game_by_year(matches: List[str]) -> List[str]:
    """Returns games made in a specific year."""
    year = int(matches[0])
    page = games_api.list_games_by_year(year, limit=25)
    games = _extract_docs(page)
    return _names_list(games)

def game_by_year_with_limit(matches: List[str]) -> List[str]:
    """Returns up to N games made in a specific year."""
    limit = int(matches[0])
    year = int(matches[1])
    page = games_api.list_games_by_year(year, limit=limit)
    games = _extract_docs(page)
    return _names_list(games)

def game_by_year_range(matches: List[str]) -> List[str]:
    """Returns games made between two years."""
    y1, y2 = int(matches[0]), int(matches[1])
    results: List[str] = []
    for year in range(min(y1, y2), max(y1, y2) + 1):
        page = games_api.list_games_by_year(year, limit=50)
        games = _extract_docs(page)
        results.extend(_names_list(games))
    return results or ["No answers"]

def game_before_year(matches: List[str]) -> List[str]:
    """Returns games made before a specific year."""
    year = int(matches[0])
    results: List[str] = []
    # Pull by decade for efficiency
    for decade in range(1900, (year // 10) * 10 + 1, 10):
        page = games_api.list_games_by_decade(decade, limit=100)
        games = _extract_docs(page)
        for g in games:
            ry = g.get("release_year")
            if isinstance(ry, (int, float)) and ry < year:
                results.append(f"- {g.get('display_name', '?')}")
    return results or ["No answers"]

def game_after_year(matches: List[str]) -> List[str]:
    """Returns games made after a specific year."""
    year = int(matches[0])
    results: List[str] = []
    for decade in range((year // 10) * 10, 2100, 10):
        page = games_api.list_games_by_decade(decade, limit=100)
        games = _extract_docs(page)
        for g in games:
            ry = g.get("release_year")
            if isinstance(ry, (int, float)) and ry > year:
                results.append(f"- {g.get('display_name', '?')}")
    return results or ["No answers"]

def maker_by_game(matches: List[str]) -> List[str]:
    """Returns the maker of a specific game."""
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    maker = g.get("developer") or g.get("publisher") or "Unknown"
    return [str(maker)]

def game_by_maker(matches: List[str]) -> List[str]:
    """Returns games made by a specific maker."""
    maker = matches[0]
    page = games_api.list_games_by_developer(maker, limit=50)
    games = _extract_docs(page)
    if not games:
        page = games_api.list_games_by_publisher(maker, limit=50)
        games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def year_by_game(matches: List[str]) -> List[str]:
    """Returns the year a game was made."""
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    y = g.get("release_year", "Unknown")
    if isinstance(y, (int, float)):
        return [str(int(y))]
    return [str(y)]

def about_game(matches: List[str]) -> List[str] | None:
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    
    title = g.get("display_name") or game
    summary = g.get("summary") or "No summary"
    price = g.get("price_model") or "unknown"
    year = g.get("release_year")
    dev = g.get("developer") or "unknown"
    pub = g.get("publisher") or "unknown"
    rating = g.get("rating")
    playtime = g.get("playtime_hours")
    is_vr = g.get("is_vr")
    plats_list = g.get("platforms") or []
    genres_list = g.get("genre") or []
    tags_list = g.get("tags") or []
    story_focus = g.get("story_focus")
    multiplayer_list = g.get("multiplayer_type") or []
    has_microtransactions = g.get("has_microtransactions")
    requires_online = g.get("requires_online")
    has_mods = g.get("has_mods")
    procedurally_generated = g.get("procedurally_generated")
    franchise = g.get("franchise")

    # Build details table
    details_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    details_table.add_column("Field", style="bold magenta")
    details_table.add_column("Value", style="cyan")
    
    if year is not None:
        details_table.add_row("Year", str(int(year) if isinstance(year, (int, float)) else year))
    if franchise:
        details_table.add_row("Franchise", str(franchise))
    details_table.add_row("Price", price)
    details_table.add_row("Developer", dev)
    details_table.add_row("Publisher", pub)
    if story_focus:
        details_table.add_row("Story Focus", str(story_focus))
    if multiplayer_list:
        details_table.add_row("Multiplayer", ", ".join(multiplayer_list))
    if rating is not None:
        details_table.add_row("Rating", f"{rating} ⭐")
    if playtime is not None:
        details_table.add_row("Playtime", f"{playtime} hours")
    if is_vr is not None:
        details_table.add_row("VR Support", "✓" if is_vr else "✗")
    if has_microtransactions is not None:
        details_table.add_row("Microtransactions", "✓" if has_microtransactions else "✗")
    if requires_online is not None:
        details_table.add_row("Requires Online", "✓" if requires_online else "✗")
    if has_mods is not None:
        details_table.add_row("Has Mods", "✓" if has_mods else "✗")
    if procedurally_generated is not None:
        details_table.add_row("Procedural Generation", "✓" if procedurally_generated else "✗")
    if plats_list:
        details_table.add_row("Platforms", ", ".join(plats_list[:5]))
    if genres_list:
        details_table.add_row("Genres", ", ".join(genres_list))
    if tags_list:
        details_table.add_row("Tags", ", ".join(tags_list[:10]))

    # Create panel with summary and details
    content = f"[bold]{summary}[/bold]\n\n"
    console.print(Panel(content, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))
    console.print(details_table)
    
    return None  # Already rendered via console


def show_edit_instructions(matches: List[str]) -> List[str] | None:
    """Render a concise, beautiful UI explaining ways to edit games."""
    header = "[bold cyan]How to Edit Games[/bold cyan]"
    intro = (
        "You can open the editor in several ways. \nAfter opening, use the menu to Request changes (LLM revision) or save to the database."
    )

    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("Action", style="bold magenta", no_wrap=True)
    table.add_column("Examples", style="cyan")

    table.add_row(
        "After viewing details",
        "edit\nmake changes",
    )
    table.add_row(
        "Edit by name",
        "edit portal\nmake changes to skyrim",
    )
    table.add_row(
        "Tips",
        "• Arrow keys navigate. ESC cancels prompts.\n• 'edit' uses the last game you selected.",
    )

    console.print(Panel(header, border_style="cyan"))
    console.print(Panel(intro, border_style="cyan"))
    console.print(table)
    return None


def open_edit_for_last_game(matches: List[str]) -> List[str] | None:
    """Open the edit UI using the last selected game, if any.

    If no game was selected in this session yet, prompt the user to choose one.
    """
    global _last_selected_game
    g = _last_selected_game
    # If an explicit title is provided after the command, try to resolve it
    if matches:
        maybe_title = matches[0]
        if maybe_title and maybe_title.strip():
            resolved = resolve_game_interactively(maybe_title)
            if resolved:
                g = resolved
                _last_selected_game = g
    if not g:
        return ["No answers"]
    try:
        from game_editor import open_edit_ui_with_existing_json  # type: ignore
        open_edit_ui_with_existing_json(g)
        return None
    except Exception:
        return ["No answers"]

def list_games_by_franchise(matches: List[str]) -> List[str]:
    # Accept: [franchise] or [limit, franchise]
    if len(matches) == 2 and matches[0].isdigit():
        limit = int(matches[0])
        franchise = matches[1]
    else:
        franchise = matches[0]
        limit = 25
    page = games_api.list_games_by_franchise(franchise, limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_platforms_for_game(matches: List[str]) -> List[str]:
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    plats = g.get("platforms") or []
    return ["Platforms:"] + _bullets(plats) if plats else ["No answers"]

def list_genres_for_game(matches: List[str]) -> List[str]:
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    genres = g.get("genre") or []
    return ["Genres:"] + _bullets(genres) if genres else ["No answers"]

def list_tags_for_game(matches: List[str]) -> List[str]:
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    tags = g.get("tags") or []
    return ["Tags:"] + _bullets(tags) if tags else ["No answers"]

def list_vr_games(matches: List[str]) -> List[str]:
    limit = _parse_limit(matches, default=25)
    page = games_api.list_games_by_vr(True, limit=limit)
    games = _extract_docs(page)
    # Backfill with 'vr' tag if fewer than requested
    if len(games) < limit:
        tag_page = games_api.list_games_by_tag("vr", limit=limit - len(games))
        tag_games = _extract_docs(tag_page)
        # De-duplicate by id if present or by display_name as fallback
        seen_keys = set()
        def key(g: dict) -> str:
            gid = g.get("_id")
            if isinstance(gid, str):
                return gid
            name = g.get("display_name")
            return f"name::{name}" if name else str(g)
        for g in games:
            seen_keys.add(key(g))
        for g in tag_games:
            k = key(g)
            if k not in seen_keys:
                games.append(g)
                seen_keys.add(k)
            if len(games) >= limit:
                break
    return _names_list(games[:limit]) or ["No answers"]

def list_requires_online_games(matches: List[str]) -> List[str]:
    limit = _parse_limit(matches, default=25)
    page = games_api.list_games_by_requires_online(True, limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_free_to_play(matches: List[str]) -> List[str]:
    limit = _parse_limit(matches, default=25)
    page = games_api.list_games_by_price_model("free-to-play", limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_paid_games(matches: List[str]) -> List[str]:
    limit = _parse_limit(matches, default=25)
    page = games_api.list_games_by_price_model("paid", limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_highly_rated(matches: List[str]) -> List[str]:
    # Patterns may be: [min] or [limit, min]
    if len(matches) == 2:
        limit = int(matches[0])
        min_rating = float(matches[1])
    else:
        min_rating = float(matches[0]) if matches else 4.0
        limit = 25
    page = games_api.list_games_by_rating_at_least(min_rating, limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_short_games(matches: List[str]) -> List[str]:
    # Patterns may be: [max_hours] or [limit, max_hours]
    if len(matches) == 2:
        limit = int(matches[0])
        max_hours = float(matches[1])
    else:
        max_hours = float(matches[0]) if matches else 5.0
        limit = 25
    page = games_api.list_games_by_playtime_at_most(max_hours, limit=limit)
    games = _extract_docs(page)
    return _names_list(games) or ["No answers"]

def list_games_tagged(matches: List[str]) -> List[str]:
    # Two variants: [tag] or [limit, tag]
    if len(matches) == 2 and matches[0].isdigit():
        limit = int(matches[0])
        tag = matches[1]
    else:
        tag = matches[0]
        limit = 25
    # Ignore meaningless tags
    if (tag or "").strip().lower() in {"game", "games"}:
        return ["I don't understand"]
    # Try normalized candidates for better recall
    for candidate in _normalize_tag_candidates(tag):
        page = games_api.list_games_by_tag(candidate, limit=limit)
        games = _extract_docs(page)
        if games:
            return _names_list(games)
    # Fallback to original
    page = games_api.list_games_by_tag(tag, limit=limit)
    games = _extract_docs(page)
    if games:
        return _names_list(games)
    # Try franchise aliases as a final fallback (e.g., "gta" -> "Grand Theft Auto")
    for fran in _normalize_franchise_candidates(tag):
        page = games_api.list_games_by_franchise(fran, limit=limit)
        games = _extract_docs(page)
        if games:
            return _names_list(games)
    return ["No answers"]

def list_games_tagged_flexible(matches: List[str]) -> List[str]:
    # Accept: [tag] or [limit, tag]
    if len(matches) == 2 and matches[0].isdigit():
        limit = int(matches[0])
        tag = matches[1]
    elif len(matches) == 1:
        # Support a single capture like "100 metroidvanias"
        parts = str(matches[0]).strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            limit = int(parts[0])
            tag = parts[1]
        else:
            tag = matches[0]
            limit = 25
    else:
        tag = matches[0]
        limit = 25
    # Ignore meaningless tags
    if (tag or "").strip().lower() in {"game", "games"}:
        return ["I don't understand"]
    tag = _singularize_tag(tag)
    for candidate in _normalize_tag_candidates(tag):
        page = games_api.list_games_by_tag(candidate, limit=limit)
        games = _extract_docs(page)
        if games:
            return _names_list(games)
    # Try raw tag
    page = games_api.list_games_by_tag(tag, limit=limit)
    games = _extract_docs(page)
    if games:
        return _names_list(games)
    # As a last resort, try franchise lookup including aliases/synonyms
    for fran in _normalize_franchise_candidates(tag):
        page = games_api.list_games_by_franchise(fran, limit=limit)
        games = _extract_docs(page)
        if games:
            return _names_list(games)
    return ["No answers"]

def is_free_game(matches: List[str]) -> List[str]:
    game = matches[0]
    g = resolve_game_interactively(game)
    if not g:
        return ["No answers"]
    pm = (g.get("price_model") or "").replace(" ", "").lower()
    is_free = pm in ("free", "freetoplay", "free-to-play")
    return ["yes" if is_free else "no"]

def bye_action(matches: List[str]) -> List[str]:
    return ["Goodbye!"]

def show_help(matches: List[str]) -> List[str] | None:
    intro = (
        "[bold cyan]NotSteam[/bold cyan] — Natural language queries you can try:\n"
        "Type sentences like these; arrow keys navigate history."
    )
    examples = [
        ("Find by year", [
            "what games were made in 2015",
            "what games were made between 2005 and 2010",
            "what games were made before 1999",
            "what games were made after 2018",
        ]),
        ("About a game", [
            "what is portal about",
            "tell me about outer wilds",
            "what platforms is skyrim on",
            "what genres is halo",
            "what tags does minecraft have",
        ]),
        ("Editing", [
            "edit",
            "edit portal",
            "make changes",
            "make changes to skyrim",
        ]),
        ("By maker", [
            "who made DOOM",
            "what games were made by Nintendo",
            "show me games made by ID Software",
        ]),
        ("Filters", [
            "show me free to play games",
            "show me paid games",
            "games rated at least 4.2",
            "games under 6 hours",
            "show me 50 vr games",
            "show me 30 online games",
        ]),
        ("Tags/Genres", [
            "show me roguelikes",
            "show soulslike games",
            "show 20 metroidvanias",
            "show me games tagged roguelike",
        ]),
        ("Other", [
            "is half life alyx free",
            "when was doom eternal made",
            "add a game",
        ])
    ]

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Topic", style="bold magenta", no_wrap=True)
    table.add_column("Examples", style="cyan")

    for topic, lines in examples:
        table.add_row(topic, "\n".join(f"• {l}" for l in lines))

    console.print(Panel(intro, border_style="cyan"))
    console.print(table)
    console.print("[dim]Tip: You can also use 'show me N ...' to grab more results.[/dim]")
    return None

# Open the Add Game UI via natural language
def open_add_game_ui(matches: List[str]) -> List[str] | None:
    # Require OpenAI key; if missing, show message and exit the interface
    has_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN"))
    if not has_key:
        try:
            # Import only to render the friendly message
            from game_editor import print_openai_missing_warning  # type: ignore
            print_openai_missing_warning()
        except Exception:
            console.print("[yellow]Add Game requires an OpenAI API key. Set OPENAI_API_KEY and restart.[/yellow]")
        # Stay in the interface; return to the prompt
        return None
    try:
        from game_editor import add_game_ui
        add_game_ui()
        return None
    except Exception:
        console.print("[red]Unable to open the game editor right now.[/red]")
        return ["No answers"]

# The pattern-action list for the natural language query system
# A list of tuples of pattern and action
pa_list: List[Tuple[List[str], Callable[[List[str]], List[Any]]]] = [
    # Editor commands
    (str.split("add a game"), open_add_game_ui),
    (str.split("add game"), open_add_game_ui),
    (str.split("create game"), open_add_game_ui),
    (str.split("new game"), open_add_game_ui),
    # Quick edit commands
    (str.split("edit"), open_edit_for_last_game),
    (str.split("edit %"), open_edit_for_last_game),
    (str.split("make changes"), open_edit_for_last_game),
    (str.split("make changes to %"), open_edit_for_last_game),
    # Help for editing
    (str.split("how do i edit"), show_edit_instructions),
    (str.split("how to edit"), show_edit_instructions),
    (str.split("help"), show_help),
    (str.split("commands"), show_help),
    (str.split("how do i use this"), show_help),
    (str.split("?"), show_help),
    (str.split("what games were made in _"), game_by_year),
    # Explicit limit + year variants
    (str.split("show me _ games made in _"), game_by_year_with_limit),
    (str.split("show _ games made in _"), game_by_year_with_limit),
    (str.split("what games were made between _ and _"), game_by_year_range),
    (str.split("what games were made before _"), game_before_year),
    (str.split("what games were made after _"), game_after_year),
    (str.split("who made %"), maker_by_game),
    (str.split("what games were made by %"), game_by_maker),
    (str.split("show me games made by %"), game_by_maker),
    (str.split("show games made by %"), game_by_maker),
    (str.split("when was % made"), year_by_game),
    (str.split("what is % about"), about_game),
    (str.split("whats % about"), about_game),
    (str.split("what's % about"), about_game),
    (str.split("tell me about %"), about_game),
    (str.split("describe %"), about_game),
    (str.split("what is %"), about_game),
    (str.split("what platforms is % on"), list_platforms_for_game),
    (str.split("what genres is %"), list_genres_for_game),
    (str.split("what genre is %"), list_genres_for_game),
    (str.split("what tags does % have"), list_tags_for_game),
    # Franchise (explicit cues only to avoid collisions with tags)
    (str.split("show % franchise games"), list_games_by_franchise),
    (str.split("show me % franchise games"), list_games_by_franchise),
    (str.split("show games in the % franchise"), list_games_by_franchise),
    (str.split("show me games in the % franchise"), list_games_by_franchise),
    # VR
    (str.split("show vr games"), list_vr_games),
    (str.split("show me vr games"), list_vr_games),
    (str.split("show _ vr games"), list_vr_games),
    (str.split("show me _ vr games"), list_vr_games),
    (str.split("show % vr games"), list_vr_games),
    (str.split("show me % vr games"), list_vr_games),
    # Online
    (str.split("show online games"), list_requires_online_games),
    (str.split("show me online games"), list_requires_online_games),
    (str.split("show _ online games"), list_requires_online_games),
    (str.split("show me _ online games"), list_requires_online_games),
    (str.split("show % online games"), list_requires_online_games),
    (str.split("show me % online games"), list_requires_online_games),
    # Free to play
    (str.split("show free to play games"), list_free_to_play),
    (str.split("show me free to play games"), list_free_to_play),
    (str.split("show _ free to play games"), list_free_to_play),
    (str.split("show me _ free to play games"), list_free_to_play),
    (str.split("show % free to play games"), list_free_to_play),
    (str.split("show me % free to play games"), list_free_to_play),
    # Paid
    (str.split("show paid games"), list_paid_games),
    (str.split("show me paid games"), list_paid_games),
    (str.split("show _ paid games"), list_paid_games),
    (str.split("show me _ paid games"), list_paid_games),
    (str.split("show % paid games"), list_paid_games),
    (str.split("show me % paid games"), list_paid_games),
    # Ratings & playtime
    (str.split("games rated at least _"), list_highly_rated),
    (str.split("show me games rated at least _"), list_highly_rated),
    (str.split("show _ games rated at least _"), list_highly_rated),
    (str.split("games under _ hours"), list_short_games),
    (str.split("show me games under _ hours"), list_short_games),
    (str.split("show _ games under _ hours"), list_short_games),
    # Tags
    (str.split("show me games tagged %"), list_games_tagged),
    (str.split("show me _ games tagged %"), list_games_tagged),
    (str.split("show _ games tagged %"), list_games_tagged),
    # Flexible tag queries after specific ones to avoid collisions
    (str.split("show me _ % games"), list_games_tagged_flexible),
    (str.split("show me % games"), list_games_tagged_flexible),
    (str.split("show _ % games"), list_games_tagged_flexible),
    (str.split("show % games"), list_games_tagged_flexible),
    (str.split("show me %"), list_games_tagged_flexible),
    (str.split("show %"), list_games_tagged_flexible),
    # Other
    (str.split("is % free"), is_free_game),
    (str.split("is % free to play"), is_free_game),
    (["bye"], bye_action),
]

def search_pa_list(src: List[str]) -> List[str] | None:
    """Takes source, finds matching pattern and calls corresponding action. If it finds
    a match but has no answers it returns ["No answers"]. If it finds no match it
    returns ["I don't understand"].

    Args:
        source - a phrase represented as a list of words (strings)

    Returns:
        a list of answers. Will be ["I don't understand"] if it finds no matches and
        ["No answers"] if it finds a match but no answers. Returns None if handler
        already rendered output directly.
    """
    # Short-circuit extremely vague inputs
    joined = " ".join(w.lower() for w in src).strip()
    if not src or joined in {"show", "show me", "show games"}:
        return ["I don't understand"]

    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            # Treat empty captures as no-match to avoid nonsense on vague inputs
            if any((m is None) or (str(m).strip() == "") for m in mat):
                continue
            answer = act(mat)
            if answer is None:
                return None  # Handler already rendered
            return answer if answer else ["No answers"]
    return ["I don't understand"]

def query_loop() -> None:
    """The simple query loop. The try/except structure is to catch Ctrl-C or Ctrl-D
    characters and exit gracefully.
    """
    # Compute OpenAI key status and render inside the intro panel
    _has_oai = bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN"))
    status_word = "[green]available[/green]" if _has_oai else "[red]unavailable[/red]"
    intro_content = (
        f"[bold cyan]NotSteam[/bold cyan] [magenta]v{VERSION}[/magenta]\n"
        "[dim]Ask me anything about games![/dim]\n"
        f"[dim]OpenAI:[/dim] {status_word}"
    )
    console.print(Panel.fit(intro_content, border_style="bright_blue"))
    console.print("")
    console.print("[dim]Tip: type [bold green]help[/bold green] to see available commands.[/dim]")
    console.print()
    
    while True:
        try:
            console.print()
            try:
                # Use prompt_toolkit for history + arrow navigation
                query_text = _session.prompt("Your query? ", completer=_completer, bottom_toolbar=_bottom_toolbar)
            except Exception:
                # Fallback to rich input
                query_text = console.input("[bold green]Your query?[/bold green] ")
            # Do not lowercase; split preserves original casing for capture groups
            sanitized = query_text.replace("?", "").strip()
            query = sanitized.split()
            
            # Check for exit condition (support common synonyms)
            joined_lower = " ".join(w.lower() for w in query).strip()
            if joined_lower in {"bye", "exit", "quit", "q"}:
                console.print("\n[yellow]So long![/yellow]\n")
                break
            
            answers = search_pa_list(query)
            if answers is None:
                # Handler already rendered output via rich console
                pass
            elif answers:
                for a in answers:
                    if a:  # Skip empty lines
                        console.print(a)
            else:
                console.print("[yellow]No answers[/yellow]")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]So long![/yellow]\n")
            break
    

def main():
    """Main entry point for the program."""
    query_loop()

if __name__ == "__main__":
    main()