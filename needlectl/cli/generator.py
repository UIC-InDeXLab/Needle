from typing import List, Optional

import typer

from backend.api_client import BackendClient
from cli.utils import print_result

generator_app = typer.Typer(help="Manage image generators (shared with the desktop app).")


def _prefs(client: BackendClient):
    return client.get_generator_preferences()


def _require_engine(prefs, name: str):
    names = [e["name"] for e in prefs.get("engines", [])]
    if name not in names:
        typer.echo(f"Unknown generator '{name}'. Available: {', '.join(names)}")
        raise typer.Exit(code=1)


@generator_app.command("list")
def generator_list(ctx: typer.Context):
    """Show generators in priority order, and whether each is enabled and usable."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    details = {g["name"]: g for g in client.list_generators()}

    if ctx.obj["output"] != "human":
        return print_result(prefs, ctx.obj["output"])

    typer.echo(f"Fallback chain: {'on' if prefs.get('fallback', True) else 'off'}")
    typer.echo("")
    for i, engine in enumerate(prefs.get("engines", []), start=1):
        info = details.get(engine["name"], {})
        if engine.get("enabled"):
            state = "enabled"
        elif engine.get("available"):
            state = "off"
        elif info.get("requires_credentials") and not info.get("credentials_set"):
            state = "off (needs an API key)"
        else:
            state = "off (unavailable)"
        model = (engine.get("params") or {}).get("model")
        typer.echo(f"{i}. {engine['name']:<14} {state}{f'  [model: {model}]' if model else ''}")
        if info.get("description"):
            typer.echo(f"   {info['description']}")


@generator_app.command("enable")
def generator_enable(ctx: typer.Context, name: str):
    """Use a generator for search."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    _require_engine(prefs, name)

    engines = prefs["engines"]
    if not prefs.get("fallback", True):
        # With the fallback chain off only one engine is ever used, so enabling
        # one has to turn the others off or the setting would be ambiguous.
        for e in engines:
            e["enabled"] = e["name"] == name
    else:
        for e in engines:
            if e["name"] == name:
                e["enabled"] = True

    result = client.set_generator_preferences(engines, prefs.get("fallback", True))
    updated = next(e for e in result["engines"] if e["name"] == name)
    if not updated["enabled"]:
        typer.echo(
            f"'{name}' cannot run yet, so it stays off. Check 'needlectl generator list'."
        )
        raise typer.Exit(code=1)
    typer.echo(f"'{name}' is now used for search.")


@generator_app.command("disable")
def generator_disable(ctx: typer.Context, name: str):
    """Stop using a generator for search."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    _require_engine(prefs, name)
    engines = prefs["engines"]
    for e in engines:
        if e["name"] == name:
            e["enabled"] = False
    client.set_generator_preferences(engines, prefs.get("fallback", True))
    typer.echo(f"'{name}' is no longer used for search.")


@generator_app.command("order")
def generator_order(ctx: typer.Context, names: List[str] = typer.Argument(
        ..., help="Generator names, highest priority first.")):
    """Set the order generators are tried in."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    for name in names:
        _require_engine(prefs, name)

    by_name = {e["name"]: e for e in prefs["engines"]}
    # Anything the user left out keeps its relative order at the end.
    ordered = [by_name[n] for n in names]
    ordered += [e for e in prefs["engines"] if e["name"] not in names]
    client.set_generator_preferences(ordered, prefs.get("fallback", True))
    typer.echo("Priority: " + " > ".join(e["name"] for e in ordered))


@generator_app.command("fallback")
def generator_fallback(ctx: typer.Context, state: str = typer.Argument(..., help="on | off")):
    """Turn the fallback chain on or off.

    On: a failing generator hands over to the next enabled one.
    Off: only the first enabled generator is used.
    """
    if state not in ("on", "off"):
        typer.echo("Expected 'on' or 'off'.")
        raise typer.Exit(code=1)
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    engines = prefs["engines"]
    if state == "off":
        keep = next((e["name"] for e in engines if e["enabled"]), None)
        for e in engines:
            e["enabled"] = e["name"] == keep
    client.set_generator_preferences(engines, state == "on")
    typer.echo(f"Fallback chain {state}.")


@generator_app.command("model")
def generator_model(ctx: typer.Context, model: str,
                    name: str = typer.Option("needle-local", help="Which generator to set it on.")):
    """Choose the model a generator should use."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    _require_engine(prefs, name)
    engines = prefs["engines"]
    for e in engines:
        if e["name"] == name:
            e["params"] = {**(e.get("params") or {}), "model": model}
    client.set_generator_preferences(engines, prefs.get("fallback", True))
    typer.echo(f"'{name}' will use '{model}'.")


@generator_app.command("models")
def generator_models(ctx: typer.Context):
    """List the on-device models and whether they are downloaded."""
    client = BackendClient(ctx.obj["api_url"])
    catalog = client.get_generate_models()

    if ctx.obj["output"] != "human":
        return print_result(catalog, ctx.obj["output"])

    if not catalog.get("available"):
        typer.echo("On-device generation is not available in this build.")
        if catalog.get("error"):
            typer.echo(f"  {catalog['error']}")
        raise typer.Exit(code=1)

    typer.echo(f"Device: {catalog.get('device', 'unknown')}")
    for m in catalog.get("models", []):
        mark = "downloaded" if m.get("downloaded") else f"{m.get('download_mb', 0)} MB download"
        typer.echo(f"  {m['id']:<14} {m.get('label', ''):<16} {mark}")
        typer.echo(f"    {m.get('description', '')}")


@generator_app.command("download")
def generator_download(ctx: typer.Context, model: str,
                       wait: bool = typer.Option(True, help="Wait for the download to finish.")):
    """Download an on-device model's weights."""
    import time

    client = BackendClient(ctx.obj["api_url"])
    client.load_generate_model(model)
    if not wait:
        typer.echo(f"Downloading '{model}' in the background.")
        return

    last = None
    while True:
        state = client.get_generate_state()
        status = state.get("state")
        if status in ("ready", "idle", "error"):
            break
        message = state.get("message") or status
        if message != last:
            typer.echo(message)
            last = message
        time.sleep(1)

    if state.get("state") == "error":
        typer.echo(f"Download failed: {state.get('message')}")
        raise typer.Exit(code=1)
    typer.echo(f"'{model}' is ready.")


@generator_app.command("test")
def generator_test(ctx: typer.Context, name: str = typer.Argument("needle-local"),
                   prompt: Optional[str] = typer.Option(None, help="Prompt to test with.")):
    """Generate one throwaway image to confirm a generator works."""
    client = BackendClient(ctx.obj["api_url"])
    prefs = _prefs(client)
    _require_engine(prefs, name)
    params = dict((next((e for e in prefs["engines"] if e["name"] == name), {}) or {}).get("params") or {})
    if prompt:
        params["prompt"] = prompt
    result = client.test_generator(name, params)
    typer.echo(f"{result['engine']} produced an image in {result['elapsed_ms'] / 1000:.1f}s.")


@generator_app.command("credentials")
def generator_credentials(ctx: typer.Context, name: str,
                          api_key: str = typer.Option(..., prompt=True, hide_input=True)):
    """Store an API key for a cloud generator."""
    client = BackendClient(ctx.obj["api_url"])
    client.set_generator_credentials(name, {"api_key": api_key})
    typer.echo(f"Saved credentials for '{name}'.")
