from __future__ import annotations

import argparse
from pathlib import Path

from openjev.importers import import_laya_playground_eval


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a locally rebuilt wdobry/laya-playground eval dataset into "
            "OpenJev benchmark JSONL without redistributing restricted source texts."
        )
    )
    parser.add_argument("playground_repo", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        count = import_laya_playground_eval(args.playground_repo, args.output)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"wrote {count} cases to {args.output}")


if __name__ == "__main__":
    main()
