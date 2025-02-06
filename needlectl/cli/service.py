# cli/service.py

import typer

from backend.api_client import BackendClient
from cli.utils import print_result
from config.config_manager import EnvConfigManager
from docker.docker_compose_manager import DockerComposeManager

service_app = typer.Typer(help="Manage Needle services.")


@service_app.command("start")
def service_start(ctx: typer.Context):
    api_url = ctx.obj["api_url"]

    typer.echo("Starting Needle services...")
    manager = DockerComposeManager()
    manager.start_containers()

    client = BackendClient(api_url)
    try:
        client.wait_for_api()
    except TimeoutError as e:
        typer.echo("API not available after backend restart.")
        raise typer.Exit(code=1)

    typer.echo("Services started.")


@service_app.command("stop")
def service_stop(ctx: typer.Context):
    typer.echo("Stopping Needle services...")
    manager = DockerComposeManager()
    manager.stop_containers()
    typer.echo("Services stopped.")


@service_app.command("restart")
def service_restart(ctx: typer.Context):
    api_url = ctx.obj["api_url"]
    typer.echo("Restarting Needle services...")

    manager = DockerComposeManager()
    manager.restart_containers()

    client = BackendClient(api_url)
    client.wait_for_api()

    typer.echo("Services restarted.")


@service_app.command("status")
def service_status_cmd(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    result = client.get_service_status()
    print_result(result, ctx.obj["output"])


@service_app.command("log")
def service_log_cmd(ctx: typer.Context):
    # Try the backend endpoint first:
    client = BackendClient(ctx.obj["api_url"])
    manager = DockerComposeManager()
    # try:
    #     result = client.get_service_log()
    #     print_result(result, ctx.obj["output"])
    # except:
    # fallback to docker compose logs
    typer.echo("Falling back to docker compose logs")
    manager.log_services("backend")


@service_app.command("config")
def service_config(
        ctx: typer.Context):
    manager = EnvConfigManager(service_name="service")
    manager.handle()
