import json

from openjev.audit_log import HashedJsonlAuditLog


def test_hash_chain_and_tamper_detection(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = HashedJsonlAuditLog(path)
    log.append("trigger", payload={"secret": "x"}, public={"probability": 0.7})
    log.append("decision", payload={"secret": "y"}, public={"decision": True})

    assert log.verify() == (True, None)

    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["public"]["probability"] = 0.1
    lines[0] = json.dumps(row, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, reason = log.verify()
    assert ok is False
    assert "hash mismatch" in reason
