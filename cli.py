from pathlib import Path
from dataclasses import asdict

import typer
from tabulate import tabulate

from helpers import build_directory_node, FilebaseService

def tabulate_objects(*object_lists: list[object], max_width: int = 30) -> None:
    if not object_lists:
        print("No lists provided")
        return

    for object_list in object_lists:
        print(
            tabulate(
                [asdict(object) for object in object_list],
                headers="keys",
                tablefmt="grid",
                maxcolwidths=max_width,
            )
        )

        print(3 * "\n")


app = typer.Typer()

@app.command()
def ingest_directory(directory_path_str: str):
    ... 