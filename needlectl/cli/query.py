from typing import Optional

import typer

from backend.api_client import BackendClient
from cli.utils import print_result
from config.config_manager import EnvConfigManager, GeneratorConfigManager

query_app = typer.Typer(help="Query the database.")


@query_app.command("run")
def search_run(ctx: typer.Context, prompt: str, n: Optional[int] = None, num_images_to_generate: Optional[int] = None,
               num_engines: Optional[int] = None, image_size: Optional[str] = None, include_base_images: Optional[bool] = None,
               use_fallback: Optional[bool] = None):
    client = BackendClient(ctx.obj["api_url"])
    manager = GeneratorConfigManager("generator")
    engine_configs = manager.request_representation

    if not engine_configs:
        typer.echo(
            "No enabled and activated generator has been found! use 'needlectl generator config' to edit generator configurations. ")
        raise typer.Exit(code=1)

    result = client.run_search(prompt=prompt, engine_configs=engine_configs, num_images_to_retrieve=n,
                               num_images_per_engine=num_images_to_generate, num_engines_to_use=num_engines, image_size=image_size,
                               include_base_images=include_base_images, use_fallback=use_fallback)
    print_result(result, ctx.obj["output"])


@query_app.command("log")
def search_log(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    result = client.get_search_logs()
    print_result(result, ctx.obj["output"])


@query_app.command("config")
def search_config(
        ctx: typer.Context):
    manager = EnvConfigManager(service_name="query")
    manager.handle()
