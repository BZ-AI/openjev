from __future__ import annotations

import json
from pathlib import Path


def import_laya_playground_eval(playground_repo: Path, output: Path) -> int:
    """Convert a locally rebuilt laya-playground eval set into OpenJev JSONL.

    The caller must obtain/rebuild the source datasets under their own licenses.
    This function does not download or redistribute any benchmark texts.
    """
    repo = playground_repo.resolve()
    tasks_path = repo / "eval" / "tasks.json"
    if not tasks_path.exists():
        raise FileNotFoundError(
            f"missing {tasks_path}; run this against a laya-playground checkout"
        )

    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    output_rows = []

    for task in tasks:
        data_path = repo / "eval" / "data" / f"{task['id']}.jsonl"
        if not data_path.exists():
            raise FileNotFoundError(
                f"missing {data_path}; run laya-playground/eval/build_dataset.py first"
            )

        for line in data_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            example = json.loads(line)
            output_rows.append(
                {
                    "id": f"{task['id']}:{example['id']}",
                    "state": example["text"],
                    "question_id": task["question_id"],
                    "question": task["question"],
                    "label": example["label"],
                    "domain": task["id"],
                    "language": "en",
                    "tags": [
                        "laya-playground-compatible",
                        "locally-rebuilt-source-data",
                    ],
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(output_rows)
