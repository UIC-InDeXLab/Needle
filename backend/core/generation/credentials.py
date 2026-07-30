"""Persistent, per-engine credential storage.

Credentials (e.g. API keys) are stored in ``<data_dir>/credentials.json`` with
restrictive permissions so users don't have to re-enter them each session.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List

from monitoring import logger
from settings import settings

_lock = threading.Lock()


def _path() -> Path:
    return Path(settings.storage.data_dir, "credentials.json")


def _load() -> Dict[str, Dict[str, str]]:
    path = _path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # corrupt file shouldn't crash the app
        logger.warning(f"Failed to read credentials file: {exc}")
        return {}


def get_credential(engine: str, key: str):
    return _load().get(engine, {}).get(key)


def set_credentials(engine: str, values: Dict[str, str]) -> None:
    with _lock:
        data = _load()
        data.setdefault(engine, {}).update({k: v for k, v in values.items() if v})
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
        try:
            path.chmod(0o600)
        except OSError:
            pass
    logger.info(f"Saved credentials for engine '{engine}'")


def credentials_set(engine: str, required: List[str]) -> bool:
    creds = _load().get(engine, {})
    return all(creds.get(key) for key in required)
