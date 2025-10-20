import os
from typing import Any, Dict, List, Optional

from convex import ConvexClient
from dotenv import load_dotenv


def _make_client() -> ConvexClient:
    load_dotenv()
    url = os.getenv("CONVEX_URL") or os.getenv("CONVEX_DEPLOYMENT")
    if not url:
        raise RuntimeError("CONVEX_URL not set")
    client = ConvexClient(url)
    token = os.getenv("CONVEX_AUTH_TOKEN") or os.getenv("CONVEX_TOKEN") or os.getenv("CONVEX_ADMIN_KEY")
    if token:
        try:
            client.set_auth(token)  # type: ignore[attr-defined]
        except Exception:
            pass
    return client


def get_game_by_id(game_id: str) -> Optional[Dict[str, Any]]:
    client = _make_client()
    return client.query("games:getGameById", {"id": game_id})


def get_game_by_name(name: str) -> Optional[Dict[str, Any]]:
    client = _make_client()
    g = client.query("games:getGameByNormalizedName", {"normalized_name": name})
    return g


def search_games_by_name(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    client = _make_client()
    return client.query("games:searchGamesByName", {"q": q, "limit": limit}) or []


def list_games_by_decade(decade: int, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"decade": decade, "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByDecade", args)


def list_games_by_year(year: int, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"year": year, "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByYear", args)


def list_games_by_platform(platform: str, decade: Optional[int] = None, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"platform": platform, "limit": limit}
    if decade is not None:
        args["decade"] = decade
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByPlatform", args)


def list_games_by_genre(genre: str, decade: Optional[int] = None, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"genre": genre, "limit": limit}
    if decade is not None:
        args["decade"] = decade
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByGenre", args)


def list_games_by_tag(tag: str, decade: Optional[int] = None, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    # Fetch until we hit limit or no more pages
    args: Dict[str, Any] = {"tag": tag, "limit": min(limit, 100)}
    if cursor is not None:
        args["cursor"] = cursor
    if decade is not None:
        args["decade"] = decade
    page = client.query("games:listGamesByTag", args)
    docs: List[Dict[str, Any]] = page.get("page") or []
    while len(docs) < limit and page and not page.get("isDone"):
        next_args: Dict[str, Any] = {
            "tag": tag,
            "limit": min(limit - len(docs), 100),
        }
        if decade is not None:
            next_args["decade"] = decade
        next_cursor = page.get("continueCursor")
        if next_cursor is not None:
            next_args["cursor"] = next_cursor
        page = client.query("games:listGamesByTag", next_args)
        docs.extend(page.get("page") or [])
    return {"page": docs[:limit], "isDone": True, "continueCursor": None}


def list_games_by_developer(developer: str, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"developer": developer, "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByDeveloper", args)


def list_games_by_publisher(publisher: str, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"publisher": publisher, "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByPublisher", args)


def list_games_by_vr(is_vr: bool, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    # Fetch until we hit limit or no more pages
    first_args: Dict[str, Any] = {"is_vr": bool(is_vr), "limit": min(limit, 100)}
    if cursor is not None:
        first_args["cursor"] = cursor
    page = client.query("games:listGamesByVR", first_args)
    docs: List[Dict[str, Any]] = page.get("page") or []
    while len(docs) < limit and page and not page.get("isDone"):
        next_args: Dict[str, Any] = {
            "is_vr": bool(is_vr),
            "limit": min(limit - len(docs), 100),
        }
        next_cursor = page.get("continueCursor")
        if next_cursor is not None:
            next_args["cursor"] = next_cursor
        page = client.query("games:listGamesByVR", next_args)
        docs.extend(page.get("page") or [])
    return {"page": docs[:limit], "isDone": True, "continueCursor": None}


def list_games_by_requires_online(requires_online: bool, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    first_args: Dict[str, Any] = {"requires_online": bool(requires_online), "limit": min(limit, 100)}
    if cursor is not None:
        first_args["cursor"] = cursor
    page = client.query("games:listGamesByOnlineRequirement", first_args)
    docs: List[Dict[str, Any]] = page.get("page") or []
    while len(docs) < limit and page and not page.get("isDone"):
        next_args: Dict[str, Any] = {
            "requires_online": bool(requires_online),
            "limit": min(limit - len(docs), 100),
        }
        next_cursor = page.get("continueCursor")
        if next_cursor is not None:
            next_args["cursor"] = next_cursor
        page = client.query("games:listGamesByOnlineRequirement", next_args)
        docs.extend(page.get("page") or [])
    return {"page": docs[:limit], "isDone": True, "continueCursor": None}


def list_games_by_price_model(price_model: str, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    first_args: Dict[str, Any] = {"price_model": price_model, "limit": min(limit, 100)}
    if cursor is not None:
        first_args["cursor"] = cursor
    page = client.query("games:listGamesByPriceModel", first_args)
    docs: List[Dict[str, Any]] = page.get("page") or []
    while len(docs) < limit and page and not page.get("isDone"):
        next_args: Dict[str, Any] = {
            "price_model": price_model,
            "limit": min(limit - len(docs), 100),
        }
        next_cursor = page.get("continueCursor")
        if next_cursor is not None:
            next_args["cursor"] = next_cursor
        page = client.query("games:listGamesByPriceModel", next_args)
        docs.extend(page.get("page") or [])
    return {"page": docs[:limit], "isDone": True, "continueCursor": None}


def list_games_by_rating_at_least(min_rating: float, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"min_rating": float(min_rating), "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByRatingAtLeast", args)


def list_games_by_playtime_at_most(max_playtime: float, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"max_playtime": float(max_playtime), "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByPlaytimeAtMost", args)


def list_games_by_franchise(franchise: str, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    client = _make_client()
    args: Dict[str, Any] = {"franchise": franchise, "limit": limit}
    if cursor is not None:
        args["cursor"] = cursor
    return client.query("games:listGamesByFranchise", args)


def update_game(game_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    client = _make_client()
    body = {"id": game_id, **payload}
    return client.mutation("ingest:updateGame", body) or {}
