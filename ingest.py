import json
from pathlib import Path
from hashlib import file_digest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pprint import pprint
import subprocess
import argparse
import shutil
from datetime import datetime, timezone

from tabulate import tabulate
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType

from viewers import wrap_text, print_current_time
from settings import storage_directory, staging_directory
from audio_recording import interactive_transcribe
from models import File, Collection
from connection import Session


def generate_sha256_hash(file_path: Path | str) -> str:
    file_path = Path(file_path)
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


def determine_created_time(file_path: Path | str) -> datetime:
    # Very specific to MacOS file system
    file_stats = file_path.stat()
    modified_timestamp = file_stats.st_mtime
    birth_timestamp = file_stats.st_birthtime

    if modified_timestamp > birth_timestamp:
        created_timestamp = birth_timestamp
    else:
        created_timestamp = modified_timestamp

    return datetime.fromtimestamp(timestamp=created_timestamp, tz=timezone.utc)


def print_recent_collections(session: SessionType):
    recent__collection_list = session.scalars(
        select(Collection).order_by(Collection.id.desc()).limit(5)
    )
    for collection in recent__collection_list:
        print(f"ID: {collection.id} | Description: {collection.description}")


def create_file(file_path: Path | str) -> File:
    file_path = Path(file_path)

    file = File(
        inserted_ts=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        sha256_hash=generate_sha256_hash(file_path=file_path),
        extension=file_path.suffix.lstrip(".").lower(),
        created_ts=determine_created_time(file_path=file_path).isoformat(timespec="seconds"),
        collection_id=None,
        description=None,
        embedding=None,
    )
    return file

def print_file_info(file: File, session: SessionType):
    data = [[
        file.id,
        file.inserted_ts,
        wrap_text(file.sha256_hash),
        file.extension,
        file.created_ts,
        file.collection_id,
        wrap_text(file.description),
    ]]

    table = tabulate(
        data,
        headers=[
            "ID",
            "Inserted TS",
            "SHA256 Hash",
            "Extension",
            "Created TS",
            "Collection ID",
            "Description",
        ]
    )

    print(10*"\n")
    print_current_time()
    print(table)


def view_and_describe(file_path: Path) -> str:
    if file_path.suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
        ".mov",
        ".mp3",
        ".mp4",
        ".avi",
    }:
        subprocess.run(["open", file_path])

    description = interactive_transcribe()
    return description


def proceed_check():
    choice = input("Press enter to proceed")
    if choice != "":
        raise (ValueError("Chose not to proceed"))


def store_file(file_path: Path, file_id: int, file_extension: str, remove: bool):
    stored_file_path = storage_directory / Path(f"{file_id}.{file_extension}")
    shutil.copy2(src=file_path, dst=stored_file_path)

    if remove:
        file_path.unlink()


def interactive_collection_creator(session: SessionType) -> Collection:
    print("Collection creator: Dictate the collection description.\n")
    description = interactive_transcribe()
    collection = Collection(
        inserted_ts=datetime.now().isoformat(), description=description, embedding=None
    )
    return collection

def print_file_list_dates(file_list: list[Path]):
    data = []
    for file in file_list:
        stats  = file.stat()
        data.append([
            file.name,
            datetime.fromtimestamp(stats.st_birthtime).isoformat(),
            datetime.fromtimestamp(stats.st_mtime)
        ])
    table = tabulate(
        data,
        headers = ["Name", "Birthtime", "Mtime"]
    )
    print(table)

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="SimpleArchive",
        description="Ingests file / collection data into database, moves to archive folder",
        epilog="By: Parsa Shemirani",
    )
    parser.add_argument("-c", "--collection", action="store_true")
    parser.add_argument("-cid", "--collection_id", type=int)
    parser.add_argument("-r", "--remove", action="store_true")
    args = parser.parse_args()

    collection_mode: bool = args.collection
    collection_id: int | None = args.collection_id
    remove_mode = args.remove
    
    file_list = [
        f
        for f in staging_directory.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]

    if collection_mode:
        print_file_list_dates(file_list=file_list)
        proceed_check()
        with Session() as session:
            with session.begin():
                if collection_id:
                    collection = session.scalar(
                        select(Collection).where(Collection.id == collection_id)
                    )
                    if not collection:
                        raise (ValueError("Collection id not found"))
                else:
                    collection = interactive_collection_creator(session=session)
                    if not collection:
                        raise (ValueError("Jamie error"))
                    session.add(collection)

            collection_id = collection.id

        for file_path in file_list:
            with Session() as session:
                with session.begin():
                    file = create_file(file_path=file_path)
                    existing_file = get_existing_file(file=file, session=session)
                    if existing_file:
                        print(f"Existing File {file_path.name} left unchanged. (Existing ID {existing_file.id})")
                    else:
                        file.collection_id = collection_id
                        session.add(file)
                if not existing_file:
                    store_file(file_path=file_path, file_id=file.id, file_extension=file.extension, remove=remove_mode)
                    
    else:
        for file_path in file_list:
            print(f"Ingesting file: {file_path}\n")
            with Session() as session:
                with session.begin():
                    file = create_file(file_path=file_path)
                    print_file_info(file=file, session=session)
                    proceed_check()
                    description = view_and_describe(file_path=file_path)
                    if get_existing_file(file=file, session=session):
                        raise (FileExistsError("Duplicate file detected."))
                    file.description = description
                    session.add(file)

                store_file(file_path=file_path, file_id=file.id, file_extension=file.extension, remove=remove_mode)


if __name__ == "__main__":
    main()
