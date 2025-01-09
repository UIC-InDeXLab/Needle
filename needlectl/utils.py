import os
from pathlib import Path

import typer


def get_storage_dir():
    needle_home_path = os.getenv("NEEDLE_HOME")
    if not needle_home_path:
        typer.echo("Error: NEEDLE_HOME not set.")
        raise typer.Exit(code=1)
    return needle_home_path


def get_config_file(filename) -> Path:
    configs_path = Path(os.path.join(get_storage_dir(), "configs"))
    if not os.path.exists(configs_path):
        os.makedirs(configs_path, exist_ok=True)

    return Path(os.path.join(configs_path, filename))


def get_compose_file():
    compose_path = Path(os.path.join(get_storage_dir(), "docker-compose.yaml"))
    return Path(compose_path)
