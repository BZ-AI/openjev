from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import OpenJev
from .models import Choice, Noul, Score
from .providers import OpenAICompatibleProvider


def _load_questions(raw):
    questions = {}
    for qid, item in raw.items():
        qtype = item["type"]
        if qtype == "noul":
            questions[qid] = Noul(**item)
        elif qtype == "choice":
            questions[qid] = Choice(**item)
        elif qtype == "score":
            questions[qid] = Score(**item)
        else:
            raise ValueError(f"Unknown question type {qtype!r}")
    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenJev typed decision CLI")
    parser.add_argument("spec", type=Path, help="JSON file containing state and questions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--no-strict-schema", action="store_true")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    provider = OpenAICompatibleProvider(
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        strict_json_schema=not args.no_strict_schema,
    )
    try:
        result = OpenJev(provider).evaluate(
            state=spec["state"],
            questions=_load_questions(spec["questions"]),
        )
        print(result.model_dump_json(indent=2))
    finally:
        provider.close()


if __name__ == "__main__":
    main()
