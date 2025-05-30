import os
import subprocess
import json
import typer
import yaml
from pathlib import Path
from utils import get_compose_file


class DockerComposeManager:
    def __init__(self):
        compose_env = os.getenv("NEEDLE_COMPOSE_FILES")
        if compose_env:
            paths = compose_env.split(os.pathsep)
            self.compose_files = [Path(p) for p in paths]
        else:
            self.compose_files = [get_compose_file()]

        for path in self.compose_files:
            if not path.is_file():
                typer.echo(f"Error: docker-compose file not found: {path}")
                raise typer.Exit(code=1)

        with open(self.compose_files[0], "r") as file:
            self.compose_data = yaml.safe_load(file)

    def _docker_compose_run(self, *args):
        cmd = ["docker", "compose"]
        for path in self.compose_files:
            cmd += ["-f", str(path)]
        cmd += list(args)
        subprocess.run(cmd, check=True)

    def get_backend_version(self) -> str:
        """
        Get the backend version from the running container using docker inspect.
        Returns:
            str: The version of the backend service, or "unknown" if not found.
        """
        try:
            # Get the backend service name and image from compose file
            services = self.compose_data.get("services", {})
            backend_service = next(
                (name for name, service in services.items() if "backend" in name.lower()),
                None
            )

            if not backend_service:
                return "unknown (backend service not found)"

            # Get container ID of the running backend service
            cmd = ["docker", "compose"]
            for path in self.compose_files:
                cmd += ["-f", str(path)]
            cmd += ["ps", "-q", backend_service]
            container_id = subprocess.check_output(cmd).decode().strip()

            if not container_id:
                return "unknown (backend not running)"

            # Inspect the container to get the version label
            cmd = ["docker", "inspect", container_id]
            inspect_output = subprocess.check_output(cmd).decode()
            container_info = json.loads(inspect_output)

            if not container_info:
                return "unknown (could not inspect container)"

            # Get version from container labels
            version = container_info[0].get("Config", {}).get("Labels", {}).get("version")
            return version if version else "unknown (no version label)"

        except subprocess.CalledProcessError:
            return "unknown (error inspecting container)"
        except Exception as e:
            return f"unknown (error: {str(e)})"

    def start_containers(self):
        """Starts all containers defined in the docker-compose file."""
        self._docker_compose_run("up", "-d")

    def stop_containers(self):
        """Stops all running containers."""
        self._docker_compose_run("down")

    def restart_containers(self):
        """Restarts all containers."""
        self._docker_compose_run("down")
        self._docker_compose_run("up", "-d")

    def log_services(self, service_name):
        self._docker_compose_run("logs", service_name)

