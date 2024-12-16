#!/usr/bin/env python3

import json
import os
import subprocess
import time

import requests
import typer
import yaml
from tqdm import tqdm

app = typer.Typer(help="CLI interface for the Needle")

directory_app = typer.Typer(help="Manage directories.")
search_app = typer.Typer(help="Perform searches.")
service_app = typer.Typer(help="Manage Needle services (start, stop, restart).")

app.add_typer(directory_app, name="directory")
app.add_typer(search_app, name="search")
app.add_typer(service_app, name="service")


@app.callback()
def main(
        ctx: typer.Context,
        api_url: str = typer.Option("http://127.0.0.1:8000", help="API URL of the backend FastAPI service."),
        output: str = typer.Option("human", help="Output format: human|json|yaml")
):
    ctx.obj = {
        "api_url": api_url,
        "output": output.lower()
    }


def print_output(data, output_format):
    if output_format == "json":
        typer.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        typer.echo(yaml.safe_dump(data, sort_keys=False))
    else:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    typer.echo(f"{k}:")
                    for i in v:
                        typer.echo(f"  - {i}")
                else:
                    typer.echo(f"{k}: {v}")
        elif isinstance(data, list):
            for i in data:
                typer.echo(i)
        else:
            typer.echo(data)


def get_compose_file():
    docker_compose_path = os.getenv("NEEDLE_DOCKER_COMPOSE_FILE")
    if not docker_compose_path or not os.path.isfile(docker_compose_path):
        typer.echo("Error: NEEDLE_DOCKER_COMPOSE_FILE not set or file not found.")
        raise typer.Exit(code=1)
    return docker_compose_path


def get_storage_dir():
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, ".needle")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def get_mounted_paths_file():
    return os.path.join(get_storage_dir(), "mounted_paths.json")


def load_mounted_paths():
    file_path = get_mounted_paths_file()
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []


def save_mounted_paths(paths):
    file_path = get_mounted_paths_file()
    with open(file_path, "w") as f:
        json.dump(paths, f, indent=2)


def update_docker_compose(new_path, service_name="backend"):
    docker_compose_path = get_compose_file()

    with open(docker_compose_path, "r") as f:
        compose_data = yaml.safe_load(f)

    if "services" not in compose_data or service_name not in compose_data["services"]:
        typer.echo("Error: 'backend' service not found in docker-compose.yml.")
        raise typer.Exit(code=1)

    service = compose_data["services"][service_name]

    if "volumes" not in service:
        service["volumes"] = []

    # Use absolute path directly
    if new_path not in [v.split(":")[0] for v in service["volumes"] if isinstance(v, str)]:
        service["volumes"].append(f"{new_path}:{new_path}")

    with open(docker_compose_path, "w") as f:
        yaml.safe_dump(compose_data, f, sort_keys=False)


def docker_compose_run(*args):
    docker_compose_path = get_compose_file()
    cmd = ["docker", "compose", "-f", docker_compose_path] + list(args)
    subprocess.run(cmd, check=True)


def restart_containers():
    docker_compose_run("down")
    docker_compose_run("up", "-d")


def restart_backend():
    docker_compose_run("up", "-d", "backend")


def start_containers():
    docker_compose_run("up", "-d")


def stop_containers():
    docker_compose_run("down")


def wait_for_api(api_url, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(api_url + "/health")
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


@directory_app.command("add")
def add_directory(
        ctx: typer.Context,
        path: str,
        show_progress: bool = typer.Option(False, help="Show indexing progress")
):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]
    abs_path = os.path.abspath(path)

    mounted_paths = load_mounted_paths()
    if abs_path not in mounted_paths:
        mounted_paths.append(abs_path)
    save_mounted_paths(mounted_paths)

    update_docker_compose(abs_path)

    typer.echo("Restarting backend container...")
    restart_backend()

    typer.echo("Waiting for API to become available...")
    if not wait_for_api(api_url, timeout=120):
        typer.echo("API not available after backend restart.")
        raise typer.Exit(code=1)

    resp = requests.post(f"{api_url}/directory", json={"path": str(abs_path)})
    if resp.status_code != 200:
        typer.echo(f"Error adding directory to API: {resp.text}, path: {abs_path}")
        raise typer.Exit(code=1)

    did = resp.json()["id"]

    if output_format == "human":
        typer.echo(f"Directory '{abs_path}' added successfully, directory id: {did}.")
    else:
        print_output({"status": "Directory added successfully", "path": abs_path, "id": did}, output_format)

    if not show_progress:
        return

    typer.echo("Indexing in progress...")
    pbar = tqdm(total=100, desc="Indexing progress", unit="%")
    start_time = time.time()

    while True:
        d_resp = requests.get(f"{api_url}/directory/{did}")
        if d_resp.status_code != 200:
            pbar.close()
            typer.echo("Error checking directory status.")
            raise typer.Exit(code=1)

        data = d_resp.json()
        ratio = data["indexing_ratio"]

        pbar.n = int(ratio * 100)
        pbar.refresh()

        if ratio >= 1.0:
            pbar.close()
            if output_format == "human":
                typer.echo("Indexing complete!")
            else:
                print_output({"status": "Indexing complete", "directory_id": did}, output_format)
            break

        elapsed = time.time() - start_time
        if ratio > 0:
            eta = (elapsed / ratio) * (1.0 - ratio)
        else:
            eta = 0.0

        # Update ETA in the progress bar itself (no extra prints)
        pbar.set_postfix_str(f"ETA: {eta:.1f}s")
        time.sleep(2)


@directory_app.command("remove")
def remove_directory(ctx: typer.Context, path: str):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]
    abs_path = os.path.abspath(path)
    resp = requests.delete(f"{api_url}/directory", params={"path": abs_path})
    if resp.status_code != 200:
        typer.echo(f"Error removing directory: {resp.text}")
        raise typer.Exit(code=1)

    if output_format == "human":
        typer.echo("Directory removed successfully.")
    else:
        print_output({"status": "Directory removed successfully", "path": abs_path}, output_format)


@directory_app.command("list")
def list_directories(ctx: typer.Context):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]
    resp = requests.get(f"{api_url}/directory")
    if resp.status_code != 200:
        typer.echo(f"Error listing directories: {resp.text}")
        raise typer.Exit(code=1)

    data = resp.json()
    directories = data.get("directories", [])

    if not directories:
        if output_format == "human":
            typer.echo("No directories found.")
        else:
            print_output({"directories": []}, output_format)
        return

    if output_format == "human":
        typer.echo("Directories:")
        for d in directories:
            typer.echo(f"- ID: {d['id']}, Path: {d['path']}, Indexed: {d['is_indexed']}")
    else:
        print_output({"directories": directories}, output_format)


@directory_app.command("describe")
def directory_detail(ctx: typer.Context, did: int):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]
    resp = requests.get(f"{api_url}/directory/{did}")
    if resp.status_code != 200:
        typer.echo(f"Error retrieving directory detail: {resp.text}")
        raise typer.Exit(code=1)

    data = resp.json()
    directory = data["directory"]
    images = data["images"]
    ratio = data["indexing_ratio"]

    if output_format == "human":
        typer.echo(f"Directory ID: {directory['id']}")
        typer.echo(f"Path: {directory['path']}")
        typer.echo(f"Indexed: {directory['is_indexed']}")
        typer.echo(f"Indexing Ratio: {ratio * 100:.2f}%")
        typer.echo("Images:")
        for img_path in images:
            typer.echo(f"- {img_path}")
    else:
        print_output(data, output_format)


@search_app.command("run")
def search(ctx: typer.Context, prompt: str,
           n: int = typer.Option(20),
           k: int = typer.Option(4),
           image_size: int = typer.Option(512),
           include_base_images: bool = typer.Option(False)):
    api_url = ctx.obj["api_url"]
    output_format = ctx.obj["output"]

    q_resp = requests.post(f"{api_url}/query", json={"q": prompt})
    if q_resp.status_code != 200:
        typer.echo(f"Error creating query: {q_resp.text}")
        raise typer.Exit(code=1)
    q_data = q_resp.json()
    qid = q_data.get("qid")

    s_resp = requests.get(f"{api_url}/search/{qid}", params={
        "n": n,
        "k": k,
        "image_size": image_size,
        "include_base_images": include_base_images
    })
    if s_resp.status_code != 200:
        typer.echo(f"Error during search: {s_resp.text}")
        raise typer.Exit(code=1)

    results = s_resp.json()

    if output_format == "human":
        typer.echo("Search results:")
        for img_id in results.get("results", []):
            typer.echo(f"- {img_id}")
        if include_base_images and "base_images" in results:
            typer.echo("Base Images (encoded):")
            for base_img in results["base_images"]:
                typer.echo(f"- {base_img[:50]}...")
    else:
        print_output(results, output_format)


@service_app.command("start")
def service_start(ctx: typer.Context):
    api_url = ctx.obj["api_url"]

    typer.echo("Starting Needle services...")
    start_containers()
    wait_for_api(api_url + "/health", timeout=120)
    typer.echo("Services started.")


@service_app.command("stop")
def service_stop(ctx: typer.Context):
    typer.echo("Stopping Needle services...")
    stop_containers()
    typer.echo("Services stopped.")


@service_app.command("restart")
def service_restart(ctx: typer.Context):
    api_url = ctx.obj["api_url"]
    typer.echo("Restarting Needle services...")
    restart_containers()
    wait_for_api(api_url + "/health", timeout=120)
    typer.echo("Services restarted.")


if __name__ == "__main__":
    app()
