# cli/generator.py
import typer

from backend.api_client import BackendClient
from cli.utils import print_result
from config.config_manager import GeneratorConfigManager

generator_app = typer.Typer(help="Manage image generators.")


@generator_app.command("list")
def generator_list(ctx: typer.Context):
    """List all available generators (as retrieved from the backend)."""
    client = BackendClient(ctx.obj["api_url"])
    result = client.list_generators()
    print_result(result, ctx.obj["output"])


@generator_app.command("describe")
def generator_describe(ctx: typer.Context, name: str):
    """Describe a specific generator."""
    client = BackendClient(ctx.obj["api_url"])
    result = client.describe_generator(name)
    print_result(result, ctx.obj["output"])


@generator_app.command("config")
def generator_config(
        ctx: typer.Context,
        action: str = typer.Argument("show", help="Action to perform: edit|show|apply")
):
    manager = GeneratorConfigManager("generator")
    manager.handle(action)
