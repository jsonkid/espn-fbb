from __future__ import annotations

import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


DEFAULT_CACHE_DIR = Path("~/.cache/espn-fbb").expanduser()


@dataclass
class JsonCache:
    root: Path = DEFAULT_CACHE_DIR

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        digest = sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        path = self._path_for_key(key)
        if not path.exists():
            return None
        now = time.time()
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        expires_at = payload.get("created_at", 0) + ttl_seconds
        if expires_at < now:
            return None
        return payload.get("value")

    def set(self, key: str, value: Any) -> None:
        path = self._path_for_key(key)
        payload = {
            "created_at": time.time(),
            "value": value,
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def snapshot_key(self, league_id: str, team_id: int, matchup_period_id: int, et_date: str) -> str:
        return f"snapshot:{league_id}:{team_id}:{matchup_period_id}:{et_date}"

    def purge_old_snapshots(self, retention_days: int, now_ts: float | None = None) -> None:
        now = now_ts or time.time()
        cutoff = now - (retention_days * 24 * 60 * 60)
        for path in self.root.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            created_at = payload.get("created_at", 0)
            if created_at < cutoff:
                path.unlink(missing_ok=True)
