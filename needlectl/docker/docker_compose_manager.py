import os
import subprocess
import json
import typer
import yaml
from utils import get_compose_file


class DockerComposeManager:
    def __init__(self):
        self.docker_compose_path = get_compose_file()
        if not os.path.isfile(self.docker_compose_path):
            typer.echo("Error: docker-compose file not found.")
            raise typer.Exit(code=1)

        # Load compose file to get service information
        with open(self.docker_compose_path, "r") as file:
            self.compose_data = yaml.safe_load(file)

    def _docker_compose_run(self, *args):
        cmd = ["docker", "compose", "-f", self.docker_compose_path] + list(args)
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
            cmd = ["docker", "compose", "-f", self.docker_compose_path, "ps", "-q", backend_service]
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

    def add_volume(self, service_name, volume_path):
        """
        Adds a volume to a specific service in the docker-compose file.
        Args:
            service_name (str): The name of the service to update.
            volume_path (str): The path of the volume to add.
        Raises:
            typer.Exit: If the service is not found in the docker-compose file.
        """
        services = self.compose_data.get("services", {})
        if service_name not in services:
            typer.echo(f"Error: Service '{service_name}' not found in docker-compose.yml.")
            raise typer.Exit(code=1)

        service = services[service_name]
        volumes = service.get("volumes", [])
        # Check if the volume already exists
        if volume_path not in [v.split(":")[0] for v in volumes if isinstance(v, str)]:
            volumes.append(f"{volume_path}:{volume_path}")
            service["volumes"] = volumes
            with open(self.docker_compose_path, "w") as file:
                yaml.safe_dump(self.compose_data, file, sort_keys=False)
            typer.echo(f"Added volume '{volume_path}' to service '{service_name}'.")
        else:
            typer.echo(f"Volume '{volume_path}' already exists for service '{service_name}'.")
