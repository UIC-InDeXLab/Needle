from typing import Optional
import os
from pathlib import Path

import typer

from utils import get_storage_dir

from cli.directory import directory_app
from cli.generator import generator_app
from cli.query import query_app
from cli.service import service_app
from cli.ui import ui_app
from cli.version import VERSION as NEEDLECTL_VERSION

app = typer.Typer(help="command line interface for Needle")

# Attach subcommand groups
app.add_typer(service_app, name="service")
app.add_typer(directory_app, name="directory")
app.add_typer(query_app, name="query")
app.add_typer(generator_app, name="generator")
app.add_typer(ui_app, name="ui")


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


@app.callback()
def main(
    ctx: typer.Context,
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
    needle_home = get_storage_dir()
    
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
        "needle_home": needle_home,
    }
