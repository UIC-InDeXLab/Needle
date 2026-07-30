import os
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """Where the desktop app keeps its database, index and settings.

    needlectl talks to the same backend the app runs, so it has to resolve the
    same directory. ``NEEDLE_DATA_DIR`` wins (the app sets it when it launches
    the backend), then the historical ``NEEDLE_HOME``, then the per-platform
    application data directory Tauri uses.

    Unlike the old implementation this never aborts when the directory is
    missing: a machine with only the desktop app installed has no ``~/.needle``,
    and the CLI must still work there.
    """
    for var in ("NEEDLE_DATA_DIR", "NEEDLE_HOME"):
        value = os.getenv(var)
        if value:
            return Path(value)

    app_id = "com.needle.app"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_id
    if os.name == "nt":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / app_id
    base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / app_id


def get_storage_dir() -> str:
    """String form of :func:`get_data_dir`, for callers that expect a path."""
    return str(get_data_dir())


def get_config_file(filename) -> Path:
    """Allow override of config directory via env var NEEDLE_CONFIG_DIR."""
    config_base = os.getenv("NEEDLE_CONFIG_DIR")
    configs_path = Path(config_base) if config_base else get_data_dir() / "configs"
    configs_path.mkdir(parents=True, exist_ok=True)
    return configs_path / filename
