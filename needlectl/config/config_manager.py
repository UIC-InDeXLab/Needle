import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List

import typer

from tui.editors import EnvConfigEditor, ConfigEditorBase, GeneratorConfigEditor
from utils import get_config_file


class ConfigManager(ABC):
    def __init__(self, service_name: str):
        self.service_name = service_name

    @property
    @abstractmethod
    def editor(self) -> ConfigEditorBase:
        pass

    @property
    @abstractmethod
    def config_file(self) -> Path:
        pass

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def save(self, config: Dict[str, str]):
        pass

    def show(self) -> None:
        config = self.load()
        for k, v in config.items():
            print(f"{k}={v}")

    def edit(self):
        self.editor.run()

    def apply(self):
        from docker.docker_compose_manager import DockerComposeManager
        manager = DockerComposeManager()
        manager.start_containers()

    def handle(self, action):
        if action == "show":
            self.show()

        elif action == "edit":
            self.edit()

        elif action == "apply":
            typer.echo("Applying new configuration and restarting services...")
            self.apply()
            typer.echo("Configuration applied.")

        else:
            typer.echo("Invalid action. Use show|edit|apply")


class EnvConfigManager(ConfigManager):

    @property
    def config_file(self) -> Path:
        return get_config_file(f"{self.service_name}.env")

    @property
    def editor(self) -> ConfigEditorBase:
        return EnvConfigEditor(self.load(), self.save)

    def load(self) -> Dict[str, Any]:
        config = {}
        if not self.config_file.exists():
            return config

        with self.config_file.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                # Try to determine the type
                if value.lower() in ('true', 'false'):
                    config[key] = value.lower() == 'true'
                elif value.isdigit():
                    config[key] = int(value)
                else:
                    config[key] = value

        return config

    def save(self, config: Dict[str, Any]) -> None:
        lines = []
        for key, value in config.items():
            if isinstance(value, bool):
                value_str = str(value).lower()
            elif isinstance(value, (int, float)):
                value_str = str(value)
            else:
                # Add quotes for string values
                value_str = f'"{value}"'
            lines.append(f"{key}={value_str}")

        with self.config_file.open('w') as f:
            f.write('\n'.join(lines) + '\n')


class GeneratorConfigManager(ConfigManager):
    @property
    def editor(self) -> ConfigEditorBase:
        return GeneratorConfigEditor(self.load(), self.save)

    @property
    def config_file(self) -> Path:
        return get_config_file(f"{self.service_name}.json")

    def load(self) -> List[Dict[str, Any]]:
        try:
            with self.config_file.open('r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save(self, config: Dict[str, str]):
        with self.config_file.open("w") as f:
            json.dump(config, f, indent=2)

    @property
    def request_representation(self):
        generators: List[Dict[str, Any]] = self.load()
        request_data = []

        for generator in generators:
            if not generator.get("enabled") or not generator.get("activated"):
                # Skip any generator that isn't both enabled and activated
                continue

            # Build the 'params' dict
            required_params = generator.get("required_params", [])
            param_values = generator.get("param_values", {})

            # For each required param, grab the stored value if available, else empty string
            params_dict = {}
            for param_info in required_params:
                param_name = param_info["name"]
                params_dict[param_name] = param_values.get(param_name, "")

            # Append the processed generator to our final list
            request_data.append({
                "name": generator["name"],
                "params": params_dict
            })

        return request_data
