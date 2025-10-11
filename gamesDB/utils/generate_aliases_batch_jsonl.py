"""
Generate Batch API-ready JSONL for OpenAI /v1/responses from games.xml
This variant requests simple alias/nickname suggestions for each game title.
"""
# Note I, Aidan, did not write this. This code was written by GPT-5 and Cursor.
import argparse
import json
import os
import re
from typing import Iterable, List, Tuple


def read_games_from_xml(xml_path: str) -> List[str]:
	with open(xml_path, "r", encoding="utf-8") as f:
		content = f.read()
	# Find tags like <g1>Title</g1>, <g123>Another</g123>
	pattern = re.compile(r"<g\d+>(.*?)</g\d+>")
	games = [m.group(1).strip() for m in pattern.finditer(content)]
	# Drop empties and dedupe while preserving order
	seen = set()
	result: List[str] = []
	for g in games:
		if g and g not in seen:
			seen.add(g)
			result.append(g)
	return result


def load_json_schema(schema_path: str) -> dict:
	with open(schema_path, "r", encoding="utf-8") as f:
		return json.load(f)


def batched_requests(
		games: Iterable[str],
		schema_obj: dict,
		model: str,
		reasoning_effort: str,
) -> Iterable[Tuple[str, dict]]:
	for idx, title in enumerate(games, start=1):
		custom_id = f"alias-{idx:05d}"
		# Build a /v1/responses request body with JSON Schema formatting
		body = {
			"model": model,
			"reasoning": {"effort": reasoning_effort},
			"input": [
				{
					"role": "system",
					"content": (
						"You generate concise alias lists for video game titles using a strict JSON schema. "
						"Prefer widely used acronyms, abbreviations, or nicknames (e.g., 'BOTW' for 'The Legend of Zelda: Breath of the Wild', 'LoL' for 'League of Legends'). "
						"For obscure titles, DLCs, or when common aliases do not exist, return an empty array and set notes to null. "
						"Avoid spoilers. Keep aliases short (<= 20 characters)."
					),
				},
				{
					"role": "user",
					"content": (
						"Return a single JSON object for aliases of the game title: "
						f"{title}."
					),
				},
			],
			"text": {
				"format": {
					"type": "json_schema",
					"name": schema_obj.get("name", "game_aliases"),
					"strict": schema_obj.get("strict", True),
					"schema": schema_obj.get("schema", schema_obj),
				}
			},
		}
		yield custom_id, body


def write_jsonl(
		requests_iter: Iterable[Tuple[str, dict]],
		output_path: str,
		endpoint: str = "/v1/responses",
) -> None:
	with open(output_path, "w", encoding="utf-8") as out:
		for custom_id, body in requests_iter:
			line = {
				"custom_id": custom_id,
				"method": "POST",
				"url": endpoint,
				"body": body,
			}
			out.write(json.dumps(line, ensure_ascii=False) + "\n")


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Generate Batch API-ready JSONL for OpenAI /v1/responses (aliases) from games.xml",
	)
	parser.add_argument(
		"--xml",
		default=os.path.join(os.path.dirname(__file__), "..", "games.xml"),
		help="Path to games.xml",
	)
	parser.add_argument(
		"--schema",
		default=os.path.join(os.path.dirname(__file__), "..", "game_aliases_schema.json"),
		help="Path to game_aliases_schema.json",
	)
	parser.add_argument(
		"--out",
		default=os.path.join(os.path.dirname(__file__), "..", "games_aliases_batch.jsonl"),
		help="Output JSONL path",
	)
	parser.add_argument(
		"--model",
		default="gpt-5-nano",
		help="Model to use in each request",
	)
	parser.add_argument(
		"--effort",
		choices=["low", "medium", "high"],
		default="medium",
		help="Reasoning effort",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=0,
		help="If >0, limit number of games included",
	)
	args = parser.parse_args()

	games = read_games_from_xml(os.path.abspath(args.xml))
	if args.limit and args.limit > 0:
		games = games[: args.limit]

	schema_obj = load_json_schema(os.path.abspath(args.schema))
	requests_iter = batched_requests(
		games=games,
		schema_obj=schema_obj,
		model=args.model,
		reasoning_effort=args.effort,
	)
	write_jsonl(requests_iter, os.path.abspath(args.out))


if __name__ == "__main__":
	main()


