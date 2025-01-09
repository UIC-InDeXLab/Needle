import os
from pathlib import Path

import typer


def get_storage_dir():
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, ".needle")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def get_config_file(filename) -> Path:
    configs_path = Path(os.path.join(get_storage_dir(), "configs"))
    if not os.path.exists(configs_path):
        os.makedirs(configs_path, exist_ok=True)

    return Path(os.path.join(configs_path, filename))


def get_compose_file():
    docker_compose_path = os.getenv("NEEDLE_DOCKER_COMPOSE_FILE")
    if not docker_compose_path or not os.path.isfile(docker_compose_path):
        typer.echo("Error: NEEDLE_DOCKER_COMPOSE_FILE not set or file not found.")
        raise typer.Exit(code=1)
    return docker_compose_path
