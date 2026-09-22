import json

from openjev.audit import HashChainAuditLog


def test_hash_chain_detects_tampering(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = HashChainAuditLog(path)
    log.append("one", {"secret": "not stored raw"})
    log.append("two", {"x": 2}, probability=0.8, threshold=0.6, decision=True)
    assert log.verify() is True

    lines = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    event["decision"] = True
    lines[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert log.verify() is False

