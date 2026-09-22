from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import OpenJev
from .models import Choice, Noul, Score
from .providers import JevProvider, LayaProvider, OpenAICompatibleProvider


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
    parser.add_argument(
        "--backend",
        choices=["openai", "laya", "laya-mlx", "jev"],
        default="openai",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--task", default=None, help="Optional Laya router task override")
    parser.add_argument("--lang", default=None, help="Optional Laya router language override")
    parser.add_argument("--preload", action="store_true", help="Preload Laya router checkpoints")
    parser.add_argument("--no-strict-schema", action="store_true")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if args.backend == "openai":
        if not args.model:
            parser.error("--model is required with --backend openai")
        provider = OpenAICompatibleProvider(
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url or "http://localhost:8000/v1",
            strict_json_schema=not args.no_strict_schema,
        )
    elif args.backend == "jev":
        provider = JevProvider(
            model=args.model or "jev-latest",
            api_key=args.api_key,
            base_url=args.base_url or "https://api.typesafe.ai",
        )
    else:
        provider = LayaProvider(
            package="laya_mlx" if args.backend == "laya-mlx" else "laya",
            checkpoint=args.model,
            task=args.task,
            lang=args.lang,
            preload=args.preload,
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
