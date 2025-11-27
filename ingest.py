import shutil
from hashlib import file_digest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing_extensions import Annotated

from tabulate import tabulate
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
import typer

from env_vars import TERMINAL_PATH, STORAGE_PATH
from connection import Session
from models import File, Collection, Label, FileLabel
from audio_recording import interactive_transcribe

ISO_FMT_Z = "%Y-%m-%dT%H:%M:%S%z"


def get_sorted_files(dir_path: Path) -> list[Path] | None:
    file_paths = sorted(
        [f for f in dir_path.glob("*") if not f.name.startswith(".") and f.is_file()]
    )
    if file_paths:
        return file_paths
    else:
        return None


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def get_existing_file(file: File, session: SessionType) -> File | None:
    existing_file = session.scalar(
        select(File).where(File.sha256_hash == file.sha256_hash)
    )
    if existing_file:
        return existing_file
    else:
        return None


def determine_created_time(file_path: Path) -> datetime:
    # Very specific to MacOS file system
    file_stats = file_path.stat()
    modified_timestamp = file_stats.st_mtime
    birth_timestamp = file_stats.st_birthtime

    if modified_timestamp > birth_timestamp:
        created_timestamp = birth_timestamp
    else:
        created_timestamp = modified_timestamp

    return datetime.fromtimestamp(timestamp=created_timestamp, tz=timezone.utc)


def create_file(fp: Path) -> File:
    file = File(
        name=fp.stem,
        sha256_hash=generate_sha256_hash(fp),
        extension=fp.suffix.lstrip(".").lower(),
        size=fp.stat().st_size,
        created_ts=determine_created_time(fp).strftime(format=ISO_FMT_Z),
        collection_id=None,
        description=None
    )

    return file


def print_created_times(file_paths: list[Path]):
    name_date_table = []
    for fp in file_paths:
        name_date_table.append([fp.name, determine_created_time(fp)])
    print(
        tabulate(name_date_table, headers=["Name", "Determined Ctime"], tablefmt="grid")
    )


def main(
    description: Annotated[str, typer.Option("--description", "-d")] = None,
    collection_id: Annotated[int, typer.Option("--collection_id", "-cid")] = None,
    label_id: Annotated[int, typer.Option("--label_id", "-lid")] = None,
):

    fp_list = get_sorted_files(TERMINAL_PATH)

    print("\n\n")
    print_created_times(fp_list)
    if input("Press e to exit: ") == "e":
        exit()

    with Session() as session:
        with session.begin():
            if collection_id:
                if collection_id == -1:
                    collection = Collection(
                        name=input("Enter collection name: "),
                        parent_id=None,
                        description=interactive_transcribe()
                    )
                    session.add(collection)
                    session.flush()
                    print("Collection created:")
                    print(collection, "\n\n")
                else:
                    collection = session.scalar(select(Collection).where(Collection.id == collection_id))
                    if collection is None:
                        raise ValueError("Collection id not found")
            else:
                collection = None

            if label_id:
                if label_id == -1:
                    label = Label(
                        name=input("Enter label name: "),
                        description=interactive_transcribe()
                    )
                    session.add(label)
                    session.flush()
                    print("Label created:")
                    print(label, "\n\n")
                else:
                    label = session.scalar(select(Label).where(Label.id == label_id))
                    if label is None:
                        raise ValueError("Label id not found")
            else:
                label = None

            for fp in fp_list:
                file = create_file(fp)

                if description:
                    if description == "i":
                        file.description = interactive_transcribe()
                    else:
                        file.description = description
                
                if collection:
                    file.collection_id = collection.id

                session.add(file)
                session.flush()
                print("File added:")
                print(file, "\n\n")

                if label:
                    fl = FileLabel(file.id, label.id)
                    session.add(fl)
                    session.flush()

                    print("Label Added:")
                    print(fl, "\n\n")

                shutil.copy2(str(fp), str(STORAGE_PATH / f"{file.id}.{file.extension}"))
                fp.unlink()


    

if __name__ == "__main__":
    typer.run(main)
