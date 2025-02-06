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


def _create_template_generator_config(ctx: typer.Context):
    config_manager = GeneratorConfigManager("generator")
    client = BackendClient(ctx.obj["api_url"])

    generators = client.list_generators()

    for gen in generators:
        gen["enabled"] = False
        gen["activated"] = False

    config_manager.save(generators)


@generator_app.command("config")
def generator_config(
        ctx: typer.Context):
    manager = GeneratorConfigManager("generator")

    if not manager.config_file.exists():
        _create_template_generator_config(ctx)

    manager.handle()
