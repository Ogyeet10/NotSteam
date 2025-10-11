import os
import sys
import json
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Dict, Any, Optional, List

from convex import ConvexClient
from dotenv import load_dotenv


def iter_ndjson_lines(path: str) -> Iterable[str]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Validate JSON is well-formed, then re-dump minified for transport
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield json.dumps(obj, separators=(",", ":"))


def _call_add_game(client: ConvexClient, payload: Dict[str, Any], retries: int = 3, base_delay: float = 0.2) -> bool:
    attempt = 0
    while True:
        try:
            res = client.mutation("ingest:addGame", payload)
            return bool(res and isinstance(res, dict) and res.get("inserted"))
        except Exception:
            attempt += 1
            if attempt > retries:
                return False
            time.sleep(base_delay * (2 ** (attempt - 1)))


def _call_upsert_aliases(client: ConvexClient, payload: Dict[str, Any], retries: int = 3, base_delay: float = 0.2) -> bool:
    """Return True if any aliases were upserted, else False (counts as skipped)."""
    attempt = 0
    while True:
        try:
            res = client.mutation("ingest:upsertAliases", payload)
            # Expect shape: { _id, upserted }
            if not res or not isinstance(res, dict):
                return False
            upserted = res.get("upserted")
            return bool(isinstance(upserted, int) and upserted > 0)
        except Exception:
            attempt += 1
            if attempt > retries:
                return False
            time.sleep(base_delay * (2 ** (attempt - 1)))


def _is_alias_payload(obj: Dict[str, Any]) -> bool:
    """Detects alias-only schema: requires 'title': str and 'aliases': list[str]."""
    if not isinstance(obj, dict):
        return False
    title = obj.get("title")
    aliases = obj.get("aliases")
    if not isinstance(title, str) or not isinstance(aliases, list):
        return False
    # Ensure aliases are strings (best-effort)
    return all(isinstance(a, str) for a in aliases)


def insert_via_convex_parallel(
    make_client,
    lines: Iterable[str],
    workers: int = 32,
    max_outstanding: Optional[int] = None,
) -> Dict[str, int]:
    if max_outstanding is None:
        max_outstanding = workers * 8

    client_pool: "queue.Queue[ConvexClient]" = queue.Queue()
    for _ in range(workers):
        client_pool.put(make_client())

    inserted = 0
    skipped = 0
    futures: List[Any] = []

    def submit(payload: Dict[str, Any]):
        nonlocal futures
        def task():
            client = client_pool.get()
            try:
                if _is_alias_payload(payload):
                    return _call_upsert_aliases(client, payload)
                return _call_add_game(client, payload)
            finally:
                client_pool.put(client)
        fut = executor.submit(task)
        futures.append(fut)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            # Backpressure: if too many outstanding, drain some completions
            while len(futures) >= max_outstanding:
                done = futures.pop(0)
                try:
                    ok = done.result()
                    if ok:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1

            submit(obj)

        # Drain remaining futures
        for fut in as_completed(futures):
            try:
                ok = fut.result()
                if ok:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

    return {"inserted": inserted, "skipped": skipped}


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run push_to_convex.py <ndjson_path>")
        sys.exit(1)

    load_dotenv()

    ndjson_path = sys.argv[1]

    convex_url = os.getenv("CONVEX_URL") or os.getenv("CONVEX_DEPLOYMENT")
    if not convex_url:
        print("Error: CONVEX_URL environment variable is not set.")
        sys.exit(2)

    def make_client() -> ConvexClient:
        c = ConvexClient(convex_url)
        auth_token = os.getenv("CONVEX_AUTH_TOKEN") or os.getenv("CONVEX_TOKEN") or os.getenv("CONVEX_ADMIN_KEY")
        if auth_token:
            try:
                c.set_auth(auth_token)  # type: ignore[attr-defined]
            except Exception:
                pass
        return c

    lines = iter_ndjson_lines(ndjson_path)
    workers = int(os.getenv("IMPORT_WORKERS", "32"))
    max_outstanding = int(os.getenv("IMPORT_MAX_OUTSTANDING", str(workers * 8)))
    result = insert_via_convex_parallel(make_client, lines, workers=workers, max_outstanding=max_outstanding)
    print(json.dumps(result))


if __name__ == "__main__":
    main()


