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
from old_models import File, Collection, Description, Edge
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
    file_mode: Annotated[bool, typer.Option("--file", "-f")] = False,
    collection_mode: Annotated[bool, typer.Option("--collection", "-c")] = False,
    batch_files_no_collection: Annotated[bool, typer.Option("--batch_files", "-bf")] = False,
    add_jpegs: Annotated[bool, typer.Option("--add_jpegs", "-aj")] = False,
):
    if file_mode:
        fp_list = get_sorted_files(TERMINAL_PATH)
        fp = fp_list[0]

        file = create_file(fp)
        print(f"\n\nName: {fp.name} | Ctime: {file.created_ts}")
        if input("Press e to exit: ") == "e":
            exit()

        print("Dictate file description")
        description = Description(text=interactive_transcribe())
        description_edge = Edge(
            type="has_description", source_node=file, target_node=description
        )

        with Session() as session:
            with session.begin():
                session.add_all([file, description, description_edge])

                session.flush()
                print("File Added:")
                print(file)
                print(description)
                print(description_edge)

                shutil.copy2(str(fp), str(STORAGE_PATH / f"{file.id}.{file.extension}"))
                fp.unlink()

    if collection_mode:
        fp_list = get_sorted_files(TERMINAL_PATH)

        print("\n\n")
        print_created_times(fp_list)
        if input("Press e to exit: ") == "n":
            exit()

        collection = Collection(name=input("Collection name: "))

        print("Dictate description for this collection.\n")
        description = Description(text=interactive_transcribe())

        description_edge = Edge(
            type="has_description", source_node=collection, target_node=description
        )

        with Session() as session:
            with session.begin():
                session.add_all([collection, description, description_edge])

                session.flush()
                print("\nCollection Added:")
                print(collection)
                print(description)
                print(description_edge)

        with Session() as session:
            with session.begin():
                for fp in fp_list:
                    file = create_file(fp)
                    collection_edge = Edge(
                        type="in_collection", source_node=file, target_node=collection
                    )
                    session.add_all([file, collection_edge])

                    session.flush()
                    print("\n\nFile Added:")
                    print(file)
                    print(collection_edge)

                    shutil.copy2(
                        str(fp), str(STORAGE_PATH / f"{file.id}.{file.extension}")
                    )
                    fp.unlink()
    if batch_files_no_collection:
        fp_list = get_sorted_files(TERMINAL_PATH)

        print("\n\n")
        print_created_times(fp_list)
        if input("Press e to exit: ") == "n":
            exit()

        with Session() as session:
            with session.begin():
                for fp in fp_list:
                    file = create_file(fp)

                    session.add(file)

                    session.flush()
                    print("\n\nFile Added:")
                    print(file)

                    shutil.copy2(
                        str(fp), str(STORAGE_PATH / f"{file.id}.{file.extension}")
                    )
                    fp.unlink()

    if add_jpegs:
        fp_list = get_sorted_files(TERMINAL_PATH)
        with Session() as session:
            with session.begin():
                for fp in fp_list:
                    existing_raw_file = session.scalar(
                        select(File).where(File.name == fp.stem)
                    )
                    if not existing_raw_file:
                        print(f"File not found for: {str(fp)}")

                    ctime_diff = determine_created_time(fp) - datetime.strptime(
                        existing_raw_file.created_ts, format=ISO_FMT_Z
                    )

                    if ctime_diff < timedelta(seconds=60):
                        jpeg_file = create_file(fp)
                        jpeg_derived_edge = Edge(
                            type="camera_jpeg",
                            source_node=existing_raw_file,
                            target_node=jpeg_file,
                        )
                        session.add_all[jpeg_file, jpeg_derived_edge]
                    else:
                        print(f"File found but time diff to large for: {str(fp)}")


if __name__ == "__main__":
    typer.run(main)
