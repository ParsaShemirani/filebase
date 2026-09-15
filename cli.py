from pathlib import Path

import typer

from db_funcs import DatabaseService
from transporters import DirectoryNode


app = typer.Typer()
db = DatabaseService()


def print_tree(node: DirectoryNode, prefix: str = "") -> None:
    typer.echo(f"{prefix}{node.directory.name}/")

    child_prefix = prefix + "  "
    for directory_file in node.directory_files:
        typer.echo(f"{child_prefix}{directory_file.file_name}")

    for child in node.children:
        print_tree(child, child_prefix)


def confirm_or_abort(message: str) -> None:
    if not typer.confirm(message):
        raise typer.Abort()


@app.command("import")
def import_(directory_path_str: str) -> None:
    node = DirectoryNode.from_path(Path(directory_path_str), db)
    print_tree(node)
    confirm_or_abort("Stage files and insert database objects?")

    node.stage_files_to_outgoing()
    node.insert_to_db()


@app.command()
def retrieve(
    directory_id: str,
    output_path_str: str,
) -> None:
    node = DirectoryNode.from_db(directory_id, db)
    print_tree(node)
    confirm_or_abort("Retrieve this tree to the output path?")

    node.retrieve_to_path(Path(output_path_str))


if __name__ == "__main__":
    app()
