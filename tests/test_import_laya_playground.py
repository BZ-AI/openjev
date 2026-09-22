import json

from openjev.benchmark import load_cases
from openjev.importers import import_laya_playground_eval


def test_importer_converts_locally_rebuilt_playground_data(tmp_path):
    repo = tmp_path / "laya-playground"
    data_dir = repo / "eval" / "data"
    data_dir.mkdir(parents=True)

    tasks = [
        {
            "id": "demo",
            "question_id": "intent",
            "question": {
                "type": "choice",
                "instructions": "Which route?",
                "criteria": {"a": "A", "b": "B"},
            },
        }
    ]
    (repo / "eval" / "tasks.json").write_text(
        json.dumps(tasks),
        encoding="utf-8",
    )
    (data_dir / "demo.jsonl").write_text(
        json.dumps({"id": 1, "text": "example", "label": "a"}) + "\n",
        encoding="utf-8",
    )

    output = tmp_path / "converted.local.jsonl"
    count = import_laya_playground_eval(repo, output)

    assert count == 1
    cases = load_cases(output)
    assert len(cases) == 1
    assert cases[0].id == "demo:1"
    assert cases[0].state == "example"
    assert cases[0].label == "a"
    assert cases[0].domain == "demo"
    assert "locally-rebuilt-source-data" in cases[0].tags
