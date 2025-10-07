import argparse
import json
import os
from typing import Optional


def extract_object_from_output_line(line: str) -> Optional[str]:
	try:
		record = json.loads(line)
	except json.JSONDecodeError:
		return None
	resp = record.get("response", {}) or {}
	body = resp.get("body") or {}
	output = body.get("output") or []
	for item in output:
		if item.get("type") != "message":
			continue
		content = item.get("content") or []
		for chunk in content:
			if chunk.get("type") == "output_text":
				text = chunk.get("text")
				if not text:
					continue
				# text should be the JSON string; validate and return canonical JSON
				try:
					obj = json.loads(text)
					return json.dumps(obj, ensure_ascii=False)
				except json.JSONDecodeError:
					# If text is not pure JSON (shouldn't happen with strict schema), skip
					return None
	return None


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Strip OpenAI Batch output JSONL to raw assistant JSON objects",
	)
	parser.add_argument(
		"--input",
		required=True,
		help="Path to batch output JSONL from Files API",
	)
	parser.add_argument(
		"--out",
		default=os.path.join(os.path.dirname(__file__), "..", "games_batch_stripped.jsonl"),
		help="Output JSONL of raw objects",
	)
	args = parser.parse_args()

	input_path = os.path.abspath(args.input)
	output_path = os.path.abspath(args.out)

	count_in = 0
	count_out = 0
	with open(input_path, "r", encoding="utf-8") as src, open(output_path, "w", encoding="utf-8") as dst:
		for line in src:
			line = line.strip()
			if not line:
				continue
			count_in += 1
			obj_json = extract_object_from_output_line(line)
			if obj_json is None:
				continue
			dst.write(obj_json + "\n")
			count_out += 1

	print(f"Processed {count_in} lines, wrote {count_out} objects -> {output_path}")


if __name__ == "__main__":
	main()


