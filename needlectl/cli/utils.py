import json
from typing import Any

import typer
import yaml


def print_human_readable(data: Any, indent: int = 0):
    """
    Recursively prints data in a human-readable format with simple styling:

    - Dictionary keys are bold + colored
    - Lists items are shown with a dash
    - Values remain unstyled (but you can add style if you wish)
    """
    # Shorter references for styling options
    # See: https://typer.tiangolo.com/tutorial/style/
    style_key = lambda k: typer.style(str(k), fg=typer.colors.CYAN, bold=True)

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                # Print the key in bold and color, then recurse for the value
                typer.echo(" " * indent + f"{style_key(k)}:")
                print_human_readable(v, indent + 2)
            else:
                # Print key and value on the same line
                typer.echo(" " * indent + f"{style_key(k)}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                # Print the dash, then recursively print child items
                typer.echo(" " * indent + "-")
                print_human_readable(item, indent + 2)
            else:
                # Print the dash and the item inline
                typer.echo(" " * indent + f"- {item}")
    else:
        # For primitives (int, str, etc.)
        typer.echo(" " * indent + str(data))


def print_result(data: Any, output_format: str):
    """
    Prints the `data` in the requested format. Supported formats:
      - "json": prints JSON with indentation
      - "yaml": prints YAML
      - otherwise: prints human-readable format using recursion, with basic styling
    """
    if output_format == "json":
        typer.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        typer.echo(yaml.dump(data))
    else:
        # Print the nicely styled, human-readable format
        print_human_readable(data)
