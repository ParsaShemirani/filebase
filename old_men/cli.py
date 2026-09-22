import shutil
from pathlib import Path
from dataclasses import asdict

import typer
from tabulate import tabulate

from old_men.makers import build_directory
from old_men.workers import insert_objects
from env_vars import PENDING_STORAGE_PATH


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
    directory_path = Path(directory_path_str)
    directory_build = build_directory(directory_path, None)

    tabulate_objects(
        directory_build.directories,
        directory_build.files,
        directory_build.directory_files,
    )

    if input("Ingest objects? (y/n): ") == "y":
        insert_objects([
            *directory_build.directories,
            *directory_build.files,
            *directory_build.directory_files,
        ])

        for file_id, file_path in directory_build.file_id_path_map.items():
            file_path.rename(Path(PENDING_STORAGE_PATH / file_id))
        
    


@app.command()
def retrieve_directory(directory_id: str):
    ...


if __name__ == "__main__":
    app()