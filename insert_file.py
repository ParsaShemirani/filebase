from hashlib import file_digest
from pathlib import Path
from datetime import datetime, timezone

from tabulate import tabulate
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType

from connection import Session
from models import File, Collection, Description, Edge
from audio_recording import interactive_transcribe

ISO_FMT_Z = "%Y-%m-%dT%H:%M:%S%z"

FILE_PATH = Path("/Users/parsahome/main/inbox/ball_drop_script.md")


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
    )

    return file

def insert_file(fp: Path, desc_text: str | None = None):
    file = create_file(fp)

    if desc_text:
        description = Description(
            text=desc_text
        )
        desc_edge = Edge(
            type="has_description",
            source_node=file,
            target_node=description
        )
        with Session() as session:
            with session.begin():
                session.add_all([file, description, desc_edge])
    else:
        with Session() as session:
            with session.begin():
                session.add(File)


def create_and_insert_collection(dir_path: Path):
    file_paths = get_sorted_files(dir_path)

    name_date_table = []
    for fp in file_paths:
        name_date_table.append([fp.name, determine_created_time(fp)])

    print(tabulate(name_date_table, headers=["Name", "Determined Ctime"], tablefmt="grid"))

    if input("Press s to stop") == "s":
        exit()

    # Collection making
    c_name = input("Collection name: ")
    collection = Collection(
        name=c_name
    )

    print("Dictate description for this collection.\n")
    c_desc = interactive_transcribe()
    description = Description(
        text=c_desc
    )

    description_edge = Edge(
        type="has_description",
        source_node=collection,
        target_node=description
    )

    with Session() as session:
        with session.begin():
            session.add_all([collection, description, description_edge])
            
            session.flush()
            print("\nCollection added:")
            print(collection)
            print(description)
            print(description_edge)


    # Create and insert the files
    with Session() as session:
        with session.begin():
            for fp in file_paths:
                file = create_file(fp)
                collection_edge = Edge(
                    type="in_collection",
                    source_node=file,
                    target_node=collection
                )
                session.add_all([file, collection_edge])
                
                session.flush()
                print("\n\nFile appended:")
                print(file)
                print(collection_edge)





if __name__ == "__main__":
    #insert_file(FILE_PATH, desc_text="HELLO WORLD")
    create_and_insert_collection(Path("/Users/parsahome/main/journal"))