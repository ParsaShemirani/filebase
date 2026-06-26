import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
import typer
from tabulate import tabulate

from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Bundle, BundleFile, Directory, DirectoryFile, DirectoryBundle
from connection import Session


IGNORED_NAMES = {".DS_Store"}

TERMINAL_PATH = Path(TERMINAL_PATH_STR)
STORAGE_PATH = Path(STORAGE_PATH_STR)


def should_ignore_path(path: Path) -> bool:
    return path.name in IGNORED_NAMES


def get_current_time_str() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def get_stats_json(file_path: Path) -> str:
    stats = file_path.stat()
    stats_dict = {
        name: getattr(stats, name) for name in dir(stats) if name.startswith("st_")
    }
    return json.dumps(stats_dict, indent=2)


def create_file(file_path: Path) -> File:
    return File(
        sha256_hash=generate_sha256_hash(file_path=file_path),
        extension=file_path.suffix.lstrip(".").lower(),
        stats_json=get_stats_json(file_path=file_path),
        inserted_ts=get_current_time_str(),
        name=None,
    )


def create_bundle(directory_path: Path) -> Bundle:
    return Bundle(
        id=str(uuid.uuid4()),
        name=directory_path.name,
        inserted_ts=get_current_time_str(),
    )

def create_bundle_file(bundle: Bundle, file: File, path_str: str) -> BundleFile:
    return BundleFile(
        bundle_id=bundle.id,
        path=path_str,
        file_sha256_hash=file.sha256_hash,
        inserted_ts=get_current_time_str(),
    )

def build_bundle(directory_path: Path) -> tuple[Bundle, list[File], list[BundleFile]]:
    bundle = create_bundle(directory_path=directory_path)
    files: list[File] = []
    bundle_files: list[BundleFile] = []

    for child_path in directory_path.rglob("*"):
        if should_ignore_path(path=child_path):
            continue
        if not child_path.is_file():
            continue
            
        file = create_file(file_path=child_path)
        bundle_file = create_bundle_file(
            bundle=bundle,
            file=file,
            path_str=child_path.relative_to(directory_path).as_posix(),
        )
        files.append(file)
        bundle_files.append(bundle_file)
    return bundle, files, bundle_files

### TYPER CLI

def tabulate_objects(objects: list[object], max_width: int) -> None:
    if not objects:
        print("Empty")
        return

    print(
        tabulate(
            [asdict(object) for object in objects],
            headers="keys",
            tablefmt="grid",
            maxcolwidths=max_width,
        )
    )

app = typer.Typer()

@app.command()
def insert_bundle(directory_path_str: str):
    directory_path = Path(directory_path_str)
    bundle, files, bundle_files = build_bundle(directory_path=directory_path)

    tabulate_objects(objects=[bundle], max_width=20)
    tabulate_objects(objects=files, max_width=20)
    tabulate_objects(objects=bundle_files, max_width=20)

    if input("Copy files to terminal? (y/n): ") == "y":
        db_inserted_path = TERMINAL_PATH / "db_inserted"
        db_inserted_path.mkdir()
        for bundle_file in bundle_files:
            shutil.copy(
                src=str(directory_path / bundle_file.path),
                dst=str(db_inserted_path / bundle_file.file_sha256_hash),
            )
        print(f"All files copied to {str(db_inserted_path)}")

    print(f"Database path: {DATABASE_PATH_STR}")
    if input("Insert into database? (y/n): ") == "y":
        with Session() as session:
            with session.begin():
                session.add(bundle)
                session.add_all(files)
                session.add_all(bundle_files)
        print("All objects added to database")

@app.command()
def hello(name: str):
    print(f"Hello {name}!")

if __name__ == "__main__":
    app()