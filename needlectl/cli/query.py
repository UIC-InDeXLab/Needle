import typer

from backend.api_client import BackendClient
from cli.utils import print_result
from config.config_manager import EnvConfigManager

query_app = typer.Typer(help="Query the database.")


@query_app.command("run")
def search_run(ctx: typer.Context, prompt: str, n: int = 20, k: int = 4, image_size: int = 512,
               include_base_images: bool = False):
    client = BackendClient(ctx.obj["api_url"])
    result = client.run_search(prompt, n, k, image_size, include_base_images)
    print_result(result, ctx.obj["output"])


@query_app.command("log")
def search_log(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    result = client.get_search_logs()
    print_result(result, ctx.obj["output"])


@query_app.command("config")
def search_config(
        ctx: typer.Context,
        action: str = typer.Argument(..., help="show|edit|apply")
):
    manager = EnvConfigManager(service_name="query")
    manager.handle(action)
