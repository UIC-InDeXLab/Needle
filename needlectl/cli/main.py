import typer

from cli.directory import directory_app
from cli.generator import generator_app
from cli.query import query_app
from cli.service import service_app

app = typer.Typer(help="command line interface for Needle")

# Attach subcommand groups
app.add_typer(service_app, name="service")
app.add_typer(directory_app, name="directory")
app.add_typer(query_app, name="query")
app.add_typer(generator_app, name="generator")


@app.callback()
def main(
        ctx: typer.Context,
        api_url: str = typer.Option("http://127.0.0.1:8000", help="API URL of the backend service."),
        output: str = typer.Option("human", help="Output format: human|json|yaml")
):
    ctx.obj = {
        "api_url": api_url,
        "output": output.lower()
    }
