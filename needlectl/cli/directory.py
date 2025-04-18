# cli/directory.py
import os
import time

import requests
import typer
from tqdm import tqdm

from backend.api_client import BackendClient
from cli.utils import print_result
from config.config_manager import EnvConfigManager, DirectoryConfigManager

directory_app = typer.Typer(help="Manage directories.")


@directory_app.command("add")
def add_directory(
        ctx: typer.Context,
        path: str,
        show_progress: bool = typer.Option(False, help="Show indexing progress")
):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]
    abs_path = os.path.abspath(path)

    client = BackendClient(api_url)

    try:
        client.wait_for_api()
        resp = client.add_directory(abs_path)
    except TimeoutError as e:
        typer.echo("API not available after backend restart.")
        raise typer.Exit(code=1)
    except requests.HTTPError as e:
        typer.echo(f"Error adding directory to API: {e}")
        raise typer.Exit(code=1)

    did = resp.get("id")

    if output_format == "human":
        typer.echo(f"Directory '{abs_path}' added successfully, directory id: {did}.")
    else:
        print_result({"status": "Directory added successfully", "path": abs_path, "id": did}, output_format)

    if not show_progress:
        return

    # Show indexing progress
    typer.echo("Indexing in progress...")
    pbar = tqdm(total=100, desc="Indexing progress", unit="%")
    start_time = time.time()

    while True:
        d_resp = client.describe_directory(did)
        ratio = d_resp["indexing_ratio"]

        pbar.n = int(ratio * 100)
        pbar.refresh()

        if ratio >= 1.0:
            pbar.close()
            if output_format == "human":
                typer.echo("Indexing complete!")
            else:
                print_result({"status": "Indexing complete", "directory_id": did}, output_format)
            break

        elapsed = time.time() - start_time
        eta = (elapsed / ratio) * (1.0 - ratio) if ratio > 0 else 0.0
        pbar.set_postfix_str(f"ETA: {eta:.1f}s")
        time.sleep(2)


@directory_app.command("remove")
def remove_directory(ctx: typer.Context, path: str):
    client = BackendClient(ctx.obj["api_url"])
    abs_path = os.path.abspath(path)
    result = client.remove_directory(abs_path)
    print_result(result, ctx.obj["output"])


@directory_app.command("list")
def list_directories(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    result = client.list_directories()
    print_result(result, ctx.obj["output"])


@directory_app.command("modify")
def modify_directories(ctx: typer.Context):
    client = BackendClient(ctx.obj["api_url"])
    manager = DirectoryConfigManager(service_name="directory", backend_client=client)
    manager.handle()


@directory_app.command("describe")
def directory_detail(ctx: typer.Context, did: int):
    client = BackendClient(ctx.obj["api_url"])
    result = client.describe_directory(did)
    print_result(result, ctx.obj["output"])


@directory_app.command("config")
def directory_config(
        ctx: typer.Context,
):
    manager = EnvConfigManager(service_name="directory")
    manager.handle()
