from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class HashedJsonlAuditLog:
    """
    Append-only audit log that stores hashes of sensitive payloads by default
    and chains each event to the previous event hash.

    This is tamper-evident, not tamper-proof: a user with filesystem write access
    can replace the entire file. Anchor selected hashes elsewhere if stronger
    guarantees are required.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: str,
        *,
        payload: Any | None = None,
        public: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prev_hash = self._last_hash()
        body = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "public": public or {},
            "payload_sha256": sha256_json(payload) if payload is not None else None,
            "prev_event_sha256": prev_hash,
        }
        event_hash = sha256_json(body)
        event = {**body, "event_sha256": event_hash}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def verify(self) -> tuple[bool, str | None]:
        prev = None
        if not self.path.exists():
            return True, None
        for line_no, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            claimed = event.pop("event_sha256")
            if event.get("prev_event_sha256") != prev:
                return False, f"line {line_no}: broken prev hash"
            actual = sha256_json(event)
            if claimed != actual:
                return False, f"line {line_no}: event hash mismatch"
            prev = claimed
        return True, None

    def _last_hash(self) -> str | None:
        if not self.path.exists():
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])["event_sha256"]
