from typing import Optional

import typer

from backend.api_client import BackendClient
from cli.utils import print_result

query_app = typer.Typer(help="Search your indexed images.")


@query_app.command("run")
def search_run(
        ctx: typer.Context,
        prompt: str,
        n: Optional[int] = typer.Option(None, "--n", help="How many results to return."),
        num_images_to_generate: Optional[int] = typer.Option(
            None, help="How many query images to generate."),
        image_size: Optional[str] = typer.Option(None, help="SMALL | MEDIUM | LARGE."),
        include_base_images: Optional[bool] = typer.Option(
            None, help="Include the generated query images in the response."),
):
    """Run a search.

    Which generators are used, in what order, and whether failures fall through
    comes from the shared configuration the desktop app also edits, so both
    behave identically. Change it with `needlectl generator`.
    """
    client = BackendClient(ctx.obj["api_url"])

    prefs = client.get_generator_preferences()
    if not any(e.get("enabled") and e.get("available") for e in prefs.get("engines", [])):
        typer.echo(
            "No generator is ready. Run 'needlectl generator list' to see why, then\n"
            "'needlectl generator enable <name>'. The built-in engine also needs a\n"
            "model: 'needlectl generator download sd-turbo'."
        )
        raise typer.Exit(code=1)

    result = client.run_search(
        prompt=prompt,
        num_images_to_retrieve=n,
        num_images_per_engine=num_images_to_generate,
        image_size=image_size,
        include_base_images=include_base_images,
    )
    print_result(result, ctx.obj["output"])


@query_app.command("log")
def search_log(ctx: typer.Context):
    """List previous queries."""
    client = BackendClient(ctx.obj["api_url"])
    result = client.get_search_logs()
    print_result(result, ctx.obj["output"])
