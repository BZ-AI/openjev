from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class HashChainAuditLog:
    path: Path

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: str,
        payload: Any,
        *,
        probability: float | None = None,
        threshold: float | None = None,
        decision: bool | None = None,
    ) -> dict[str, Any]:
        if not event_type:
            raise ValueError("event_type is required")
        previous = self._last_hash()
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload_sha256": _sha256_text(_canonical_json(payload)),
            "probability": probability,
            "threshold": threshold,
            "decision": decision,
            "prev_hash": previous,
        }
        event["event_hash"] = _sha256_text(_canonical_json(event))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(event) + "\n")
        return event

    def _last_hash(self) -> str | None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(lines[-1])["event_hash"]

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        previous: str | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("prev_hash") != previous:
                return False
            event_hash = event.pop("event_hash", None)
            if event_hash != _sha256_text(_canonical_json(event)):
                return False
            previous = event_hash
        return True

