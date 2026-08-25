from pathlib import Path
from dataclasses import asdict

import typer
from tabulate import tabulate

from helpers import CatalogService, should_ignore_path_name, DirectoryNode

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
def proof_directory(directory_path_str: str):
    directory_path = Path(directory_path_str)
    for root, _, files in directory_path.walk():
        print(f"{root.relative_to(directory_path)}")

        if files:
            for file_name in files:
                if not should_ignore_path_name(file_name):
                    print(f"- {file_name}")
        else:
            print("** NO FILES **")
        print(2*"\n")


@app.command()
def import_directory(directory_path_str: str, storage_device_id: str):
    directory_path = Path(directory_path_str)
    directory_node = DirectoryNode().from_path(directory_path)

    CatalogService.add_objects([
        *directory_node.get_all_directories(),
        *directory_node.get_all_directory_files(),
        *CatalogService.get_new_files(directory_node.get_all_unique_files())
    ])





@app.command()
def retrieve_directory(directory_id: str):
    ...


if __name__ == "__main__":
    app()