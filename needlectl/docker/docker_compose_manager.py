import os
import subprocess

import typer
import yaml


class DockerComposeManager:
    def __init__(self):
        self.docker_compose_path = os.getenv("NEEDLE_DOCKER_COMPOSE_FILE", "docker-compose.yml")
        if not os.path.isfile(self.docker_compose_path):
            typer.echo("Error: docker-compose file not found.")
            raise typer.Exit(code=1)

    def _docker_compose_run(self, *args):
        cmd = ["docker", "compose", "-f", self.docker_compose_path] + list(args)
        subprocess.run(cmd, check=True)

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
        with open(self.docker_compose_path, "r") as file:
            compose_data = yaml.safe_load(file)

        services = compose_data.get("services", {})
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
                yaml.safe_dump(compose_data, file, sort_keys=False)

            typer.echo(f"Added volume '{volume_path}' to service '{service_name}'.")
        else:
            typer.echo(f"Volume '{volume_path}' already exists for service '{service_name}'.")
