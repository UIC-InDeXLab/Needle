import typer
import json
import yaml
from typing import Any

def print_result(data: Any, output_format: str):
    if output_format == "json":
        typer.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        typer.echo(yaml.dump(data))
    else:
        # human-readable format
        if isinstance(data, dict):
            for k, v in data.items():
                typer.echo(f"{k}: {v}")
        elif isinstance(data, list):
            for item in data:
                typer.echo(item)
        else:
            typer.echo(str(data))
