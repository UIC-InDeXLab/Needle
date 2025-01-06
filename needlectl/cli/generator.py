# cli/generator.py
import typer
from backend.api_client import BackendClient

from cli.utils import print_result
from config.config_manager import ConfigManager

generator_app = typer.Typer(help="Manage image generators.")


@generator_app.command("list")
def generator_list(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    result = client.list_generators()
    print_result(result, ctx.obj["output"])


@generator_app.command("describe")
def generator_describe(ctx: typer.Context, name: str):
    client = BackendClient(ctx.obj["api_url"])
    result = client.describe_generator(name)
    print_result(result, ctx.obj["output"])


@generator_app.command("config")
def generator_config(
        action: str = typer.Argument(..., help="show|set|edit|apply"),
        key: str = typer.Option(None, help="The configuration key to set"),
        value: str = typer.Option(None, help="The value to set for the key")
):
    manager = ConfigManager(service_name="generator")
    manager.handle(action, key, value)
