import os
from pathlib import Path

import typer


def get_storage_dir():
    needle_home_path = os.getenv("NEEDLE_HOME")
    if not needle_home_path:
        # Default to ~/.needle for one-liner installations
        needle_home_path = os.path.expanduser("~/.needle")
        if not os.path.exists(needle_home_path):
            typer.echo(f"Error: Needle installation not found at {needle_home_path}")
            typer.echo("Please set NEEDLE_HOME environment variable or install Needle first.")
            raise typer.Exit(code=1)
    return needle_home_path


def get_config_file(filename) -> Path:
    """Allow override of config directory via env var NEEDLE_CONFIG_DIR."""
    config_base = os.getenv("NEEDLE_CONFIG_DIR")
    if config_base:
        configs_path = Path(config_base)
    else:
        configs_path = Path(os.path.join(get_storage_dir(), "configs"))
    if not configs_path.exists():
        os.makedirs(configs_path, exist_ok=True)

    return configs_path / filename


def get_compose_file():
    compose_path = Path(os.path.join(get_storage_dir(), "docker", "docker-compose.infrastructure.yaml"))
    return Path(compose_path)
