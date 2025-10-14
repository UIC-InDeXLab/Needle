from typing import Optional
from enum import Enum
import os
from pathlib import Path

import typer

from utils import get_storage_dir

from cli.directory import directory_app
from cli.generator import generator_app
from cli.query import query_app
from cli.service import service_app
from cli.version import VERSION as NEEDLECTL_VERSION
from docker.docker_compose_manager import DockerComposeManager

app = typer.Typer(help="command line interface for Needle")

# Attach subcommand groups
app.add_typer(service_app, name="service")
app.add_typer(directory_app, name="directory")
app.add_typer(query_app, name="query")
app.add_typer(generator_app, name="generator")


def get_backend_version() -> str:
    """Get the backend version from the running service."""
    try:
        # Try to get version from running backend
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            return "running"
        else:
            return "unknown (not responding)"
    except:
        return "unknown (not running)"


def version_callback(value: bool):
    """Callback for --version flag"""
    if value:
        backend_version = get_backend_version()
        typer.echo(f"Backend version: {backend_version}")
        typer.echo(f"Needlectl version: {NEEDLECTL_VERSION}")
        raise typer.Exit()


class Profile(str, Enum):
    """Named runtime profiles for choosing prod vs dev compose/config setup."""
    dev = "dev"
    prod = "prod"


@app.callback()
def main(
    ctx: typer.Context,
    home: Optional[str] = typer.Option(
        None, "--home", "-H", help="Path to the Needle home directory"
    ),
    profile: Profile = typer.Option(
        Profile.prod,
        "--profile",
        "-P",
        help="Runtime profile (prod or dev). Default: prod",
        case_sensitive=False,
    ),
    config_dir: Optional[str] = typer.Option(
        None,
        "--config-dir",
        "-C",
        help="Override configuration directory (defaults to $NEEDLE_HOME/configs or profile-specific)",
    ),
    api_url: str = typer.Option(
        "http://127.0.0.1:8000", help="API URL of the backend service."
    ),
    output: str = typer.Option(
        "human", help="Output format: human|json|yaml"
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the backend version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    if home:
        os.environ["NEEDLE_HOME"] = home

    needle_home = get_storage_dir()
    
    if config_dir:
        os.environ["NEEDLE_CONFIG_DIR"] = config_dir
    elif profile == Profile.dev:
        os.environ["NEEDLE_CONFIG_DIR"] = str(Path(needle_home) / "configs" / "dev")

    # Set up Docker compose files for infrastructure services only
    # Check if we're in the current directory (for development) or use the home directory
    current_dir = Path.cwd()
    if (current_dir / "docker" / "docker-compose.infrastructure.yaml").exists():
        files = [current_dir / "docker" / "docker-compose.infrastructure.yaml"]
    else:
        files = [Path(needle_home) / "docker" / "docker-compose.infrastructure.yaml"]
    os.environ["NEEDLE_COMPOSE_FILES"] = os.pathsep.join(str(p) for p in files)

    ctx.obj = {
        "api_url": api_url,
        "output": output.lower(),
        "profile": profile,
        "needle_home": needle_home,
    }
