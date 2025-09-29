import json
from pathlib import Path
from hashlib import file_digest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pprint import pprint
import subprocess
import argparse
import shutil

from settings import (
    json_database_directory,
    staging_directory,
    intake_storage_device_id,
)
from audio_recording import interactive_transcribe

hashes_file_path = json_database_directory / Path("files/hashes.jsonl")
collections_directory = json_database_directory / Path("collections/")
files_directory = json_database_directory / Path("files/")
storage_devices_directory = json_database_directory / Path("storage_devices/")
embeddings_directory = json_database_directory / Path("embeddings/")


def generate_sha256_hash(file_path: Path | str) -> str:
    file_path = Path(file_path)
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def generate_shard_path(id_int: int, extension: str) -> Path:
    """
    Creates a sharded directory layout. 99 Directories
    each containing 100 files. Directory name
    is hundreds count of the number.
    """
    hundreds = id_int // 100
    shard_path = Path(f"{hundreds}/{id_int}.{extension}")

    return shard_path


def get_file_status(sha256_hash: str):
    """
    Case: File already exists:
    Returns True, and its id.

    Case: File does not exist:
    Returns false, and what id it should have.
    """
    json_list = [
        json.loads(line) for line in open(hashes_file_path, "r", encoding="utf-8")
    ]

    max_number = 0
    for item in json_list:
        item_id = item["id"]
        if item["sha256_hash"] == sha256_hash:
            return True, item_id

        if item_id > max_number:
            max_number = item_id

    return False, max_number + 1


def update_description(file_id: int, description: str):
    shard_path = generate_shard_path(id_int=file_id, extension="json")
    json_file_path = files_directory / shard_path
    json_file_path.parent.mkdir(exist_ok=True)
    with open(json_file_path, "r") as f:
        file_dict = json.load(f)

    file_dict["description"] = description

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(file_dict, f, indent=4)


def get_storage_device_path(id: int) -> Path:
    json_device_path = storage_devices_directory / Path(f"{id}.json")
    with open(json_device_path, "r") as f:
        device_dict = json.load(f)
    return Path(device_dict["path"])


def insert_file(file_path: Path | str, description: str | None = None) -> dict:
    file_path = Path(file_path)
    file_dict = {}
    file_dict["sha256_hash"] = generate_sha256_hash(file_path=file_path)
    file_exists, file_dict["id"] = get_file_status(sha256_hash=file_dict["sha256_hash"])

    if file_exists:
        if not description:
            raise FileExistsError(f"File already exists. File id: {file_dict['id']}")
        print(file_path)
        description_choice = input(
            "File exists. Update description? [y/n]"
        ).strip().lower() in ("y", "yes", "true", "1")
        if description_choice:
            update_description(file_id=file_dict["id"], description=description)
            return True
        else:
            raise FileExistsError(f"File already exists. File id: {file_dict['id']}")

    file_dict["extension"] = file_path.suffix.lstrip(".").lower()

    file_stats = file_path.stat()
    file_dict["size"] = file_stats.st_size
    pacific = ZoneInfo("America/Los_Angeles")

    modified_timestamp = file_stats.st_mtime
    modified_utc = datetime.fromtimestamp(timestamp=modified_timestamp, tz=timezone.utc)
    modified_utc_iso_format = modified_utc.isoformat()
    modified_pacific_iso_format = modified_utc.astimezone(tz=pacific).isoformat()

    birth_timestamp = file_stats.st_birthtime
    birth_utc = datetime.fromtimestamp(timestamp=birth_timestamp, tz=timezone.utc)
    birth_utc_iso_format = birth_utc.isoformat()
    birth_pacific_iso_format = birth_utc.astimezone(tz=pacific).isoformat()

    file_dict["inserted_ts"] = datetime.now().isoformat()

    if modified_timestamp > birth_timestamp:
        file_dict["created_ts"] = birth_utc_iso_format
    else:
        file_dict["created_ts"] = modified_utc_iso_format

    if description:
        file_dict["description"] = description
    else:
        file_dict["description"] = None

    """
    print("File Dict:\n")
    pprint(file_dict)
    print(f"Modified pacific iso format: {modified_pacific_iso_format}")
    print(f"Birth pacific iso format: {birth_pacific_iso_format}")

    proceed_choice = input("Proceed with inserting file? [y/n]: ").strip().lower() in (
        "y",
        "yes",
        "true",
        "1",
    )
    if not proceed_choice:
        raise (ValueError("Did not choose to proceed"))
    """

    shard_path = generate_shard_path(id_int=file_dict["id"], extension="json")
    json_file_path = files_directory / shard_path
    json_file_path.parent.mkdir(exist_ok=True)
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(file_dict, f, indent=4)

    hash_record = {"id": file_dict["id"], "sha256_hash": file_dict["sha256_hash"]}
    with open(hashes_file_path, "a", encoding="utf-8") as f:
        json.dump(hash_record, f)
        f.write("\n")

    return file_dict


def create_collection(description: str) -> int:
    single_collections_file_path = collections_directory / Path("single_file.jsonl")

    collections_list = [
        json.loads(line)
        for line in open(single_collections_file_path, "r", encoding="utf-8")
    ]
    max_number = 0
    for item in collections_list:
        item_id = item["id"]
        if item_id > max_number:
            max_number = item_id

    collection_dict = {
        "id": max_number + 1,
        "contains_files": [],
        "description": description,
    }

    shard_path = generate_shard_path(id_int=collection_dict["id"], extension="json")
    collection_file_path = collections_directory / shard_path

    with open(collection_file_path, "w", encoding="utf-8") as f:
        json.dump(collection_dict, f, indent=4)

    with open(single_collections_file_path, "a", encoding="utf-8") as f:
        json.dump(collection_dict, f)
        f.write("\n")

    return collection_dict["id"]


def print_recent_collections():
    single_collections_file_path = collections_directory / Path("single_file.jsonl")

    collections_list = [
        json.loads(line)
        for line in open(single_collections_file_path, "r", encoding="utf-8")
    ]
    last_five_list = sorted(collections_list, key=lambda x: x["id"], reverse=True)[:5]

    print("Recent collection info:\n")
    for item in last_five_list:
        print(f"ID: {item['id']} | Description: {item['description']}")
        print("\n")


def store_file(remove: bool, file_path: Path | str, file_id: int) -> Path:
    file_path = Path(file_path)
    storage_device_path = get_storage_device_path(id=intake_storage_device_id)
    shard_path = generate_shard_path(
        id_int=file_id, extension=file_path.suffix.lstrip(".").lower()
    )
    stored_file_path = storage_device_path / shard_path
    stored_file_path.parent.mkdir(exist_ok=True)
    shutil.copy(src=file_path, dst=stored_file_path)

    if remove:
        file_path.unlink()

    return stored_file_path


def ingest_file(remove: bool, file_path: Path, description_mode: bool) -> dict:
    if description_mode:
        if file_path.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".mov",
            ".mp3",
            ".mp4",
        }:
            subprocess.run(["open", file_path])

        description = interactive_transcribe()
        file_dict = insert_file(file_path=file_path, description=description)
    else:
        file_dict = insert_file(file_path=file_path)

    stored_file_path = store_file(
        remove=remove, file_path=file_path, file_id=file_dict["id"]
    )

    return(file_dict)


def ingest_collection(file_list: list):


### Command Line Time
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="SimpleArchive",
        description="Archives files in the staging area",
        epilog="By: Parsa Shemirani",
    )
    parser.add_argument("-cv", "--collection_view", action="store_true")
    parser.add_argument("-d", "--description_mode", action="store_true")
    parser.add_argument("-r", "--remove", action="store_true")
    parser.add_argument("-nc", "--new_collection", action="store_true")
    parser.add_argument("-ec", "--existing_collection", action="store_true")
    args = parser.parse_args()

    if args.collection_view:
        print_recent_collections()
        return 0

    file_list = [f for f in staging_directory.iterdir() if f.is_file()]

    # Ingest single file
    if len(file_list) == 1:
        file_path = file_list[0]
        ingest_file(
            remove=args.remove,
            file_path=file_path,
            description_mode=args.description_mode,
        )

    # Create collection, ingest and associate files.
    if len(file_list) > 1:
        collection_id = args.existing_collection
        new_collection = args.new_collection
        if collection_id:
            for file_path in file_list:
                ingest_file(
                    remove=args.remove,
                    file_path=file_path,
                    description_mode=False
                )
        elif new_collection:
            ...
        else:
            raise (ValueError("JAMIE IS IN TOWN"))

    return 0


if __name__ == "__main__":
    SystemExit(main())
