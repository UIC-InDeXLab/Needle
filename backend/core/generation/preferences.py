"""Persistent generator preferences shared by every client.

Which engines are enabled, the order they are tried in, the model each one
should use and whether failures fall through to the next engine used to live in
the browser's localStorage. That made the desktop app and ``needlectl``
disagree: enabling an engine in one was invisible to the other.

The preferences now live with the rest of the app state in
``<data_dir>/generators.json``, so whichever interface you use, you are editing
the same configuration.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from monitoring import logger
from settings import settings

_lock = threading.Lock()

#: Legacy identifiers that have since been renamed, mapped to their current id.
_ALIASES = {"remote": "needle-local", "needle-generator": "needle-local"}


def _path() -> Path:
    return Path(settings.storage.data_dir, "generators.json")


def _read() -> Dict:
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # a corrupt file must not break generation
        logger.warning(f"Failed to read generator preferences: {exc}")
        return {}


def _write(data: Dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _canonical(name: str) -> str:
    return _ALIASES.get(str(name), str(name))


def load(known_engines: List[str], default_engine: Optional[str] = None) -> Dict:
    """Return the stored preferences, reconciled against the engines that exist.

    Engines that have appeared since the preferences were written are appended
    (disabled), and entries for engines that no longer exist are dropped, so a
    rename or a new provider never leaves a stale file behind.
    """
    data = _read()
    stored = data.get("engines") or []

    by_name: Dict[str, Dict] = {}
    order: List[str] = []
    for entry in stored:
        if not isinstance(entry, dict):
            continue
        name = _canonical(entry.get("name", ""))
        if name not in known_engines or name in by_name:
            continue
        by_name[name] = {
            "name": name,
            "enabled": bool(entry.get("enabled")),
            "params": entry.get("params") or {},
        }
        order.append(name)

    for name in known_engines:
        if name not in by_name:
            by_name[name] = {"name": name, "enabled": False, "params": {}}
            order.append(name)

    engines = [by_name[n] for n in order]

    # First run: adopt the default engine so search works without a visit to the
    # settings screen. Availability is checked by the caller.
    if not stored and default_engine:
        for engine in engines:
            engine["enabled"] = engine["name"] == _canonical(default_engine)

    return {"engines": engines, "fallback": bool(data.get("fallback", True))}


def save(engines: List[Dict], fallback: bool) -> Dict:
    """Persist the full preference set (order matters: first enabled wins)."""
    cleaned = []
    seen = set()
    for entry in engines or []:
        name = _canonical((entry or {}).get("name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append({
            "name": name,
            "enabled": bool(entry.get("enabled")),
            "params": entry.get("params") or {},
        })
    with _lock:
        _write({"engines": cleaned, "fallback": bool(fallback)})
    logger.info(f"Saved generator preferences ({sum(e['enabled'] for e in cleaned)} enabled)")
    return {"engines": cleaned, "fallback": bool(fallback)}


def update_engine(name: str, *, enabled: Optional[bool] = None,
                  params: Optional[Dict] = None) -> Dict:
    """Change one engine without having to send the whole list."""
    name = _canonical(name)
    with _lock:
        data = _read()
        engines = data.get("engines") or []
        entry = next((e for e in engines if _canonical(e.get("name", "")) == name), None)
        if entry is None:
            entry = {"name": name, "enabled": False, "params": {}}
            engines.append(entry)
        if enabled is not None:
            entry["enabled"] = bool(enabled)
        if params:
            entry["params"] = {**(entry.get("params") or {}), **params}
        data["engines"] = engines
        data.setdefault("fallback", True)
        _write(data)
    return data


def search_engines(known_engines: List[str], default_engine: Optional[str] = None) -> Dict:
    """The engine chain to use for a search, in priority order.

    With fallback off only the first enabled engine is eligible, which is what
    makes "off" mean "use exactly this one".
    """
    prefs = load(known_engines, default_engine)
    enabled = [e for e in prefs["engines"] if e["enabled"]]
    if not prefs["fallback"]:
        enabled = enabled[:1]
    return {"engines": enabled, "fallback": prefs["fallback"]}
