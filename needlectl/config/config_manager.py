import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

import typer


def get_storage_dir():
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, ".needle")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def get_config_file(filename) -> Path:
    return Path(os.path.join(get_storage_dir(), "config", filename))


def get_compose_file():
    docker_compose_path = os.getenv("NEEDLE_DOCKER_COMPOSE_FILE")
    if not docker_compose_path or not os.path.isfile(docker_compose_path):
        typer.echo("Error: NEEDLE_DOCKER_COMPOSE_FILE not set or file not found.")
        raise typer.Exit(code=1)
    return docker_compose_path


class ConfigManager:

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.config_file = get_config_file(f"{service_name}.env")
        if not self.config_file.exists():
            self.config_file.touch()

    def load_config(self) -> Dict[str, str]:
        config = {}
        with self.config_file.open("r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    config[key.strip()] = value.strip()
        return config

    def save_config(self, config: Dict[str, str]) -> None:
        # Overwrite the file
        with self.config_file.open("w") as f:
            for k, v in config.items():
                f.write(f"{k}={v}\n")

    def show(self) -> None:
        config = self.load_config()
        for k, v in config.items():
            print(f"{k}={v}")

    def edit(self) -> None:
        # Use the user's editor to edit the config file
        editor = os.environ.get("EDITOR", "vi")
        # Create a temporary copy of the config file to edit
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as tmp:
            temp_path = tmp.name
            shutil.copy(self.config_file, temp_path)

        subprocess.call([editor, temp_path])

        # After editing, read back the updated config and overwrite the original
        updated_config = {}
        with open(temp_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    updated_config[key.strip()] = value.strip()

        # Save changes
        self.save_config(updated_config)
        os.remove(temp_path)

    def set(self, key: str, value: str) -> None:
        config = self.load_config()
        config[key] = value
        self.save_config(config)

    def apply(self) -> None:
        from docker.docker_compose_manager import DockerComposeManager
        manager = DockerComposeManager()
        manager.start_containers()

    def handle(self, action, key, value):
        if action == "show":
            self.show()

        elif action == "edit":
            self.edit()

        elif action == "set":
            if key is None or value is None:
                typer.echo("Please provide --key and --value for 'set' action.")
                raise typer.Exit(code=1)
            self.set(key, value)
            typer.echo(f"Set {key} to {value}.")

        elif action == "apply":
            typer.echo("Applying new configuration and restarting services...")
            self.apply()
            typer.echo("Configuration applied.")

        else:
            typer.echo("Invalid action. Use show|set|edit|apply")
