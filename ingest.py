import json
from pathlib import Path
from hashlib import file_digest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pprint import pprint

from settings import json_database_directory

hashes_file_path = json_database_directory / Path("files/hashes.jsonl")
collections_directory = json_database_directory / Path("collections/")
files_directory = json_database_directory / Path("files/")
storage_devices_directory = json_database_directory / Path("storage_devices/")
embeddings_directory = json_database_directory / Path("embeddings/")

def generate_sha256_hash(file_path: Path | str) -> str:
    file_path = Path(file_path)
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()

def generate_shard_path(kind_directory: str, id_int: int, extension: str) -> Path:
    """
    Creates a sharded directory layout.
    Max 9,801 files. 99 Directories
    each containing 99 files. Directory name
    is hundreds count of the number.
    """
    hundreds = id_int // 100
    shard_ending = Path(f"{kind_directory}/{hundreds}/{id_int}.{extension}")
    shard_path = json_database_directory / shard_ending

    # Ensure parent directory exists
    shard_path.parent.mkdir(exist_ok=True)
    return shard_path


def get_file_status(sha256_hash: str):
    """
    Case: File already exists:
    Returns True, and its id.

    Case: File does not exist:
    Returns false, and what id it should have.
    """
    objects_list = [json.loads(line) for line in open(hashes_file_path, "r", encoding="utf-8")]
    
    max_number = 0
    for object in objects_list:
        object_id = object['id']
        if object['sha256_hash'] == sha256_hash:
            return True, object_id

        if object_id > max_number:
            max_number = object_id
        
    return False, max_number + 1

def insert_file(file_path: Path | str, description: str | None = None):
    file_path = Path(file_path)
    file_dict = {}
    file_dict ['sha256_hash'] = generate_sha256_hash(file_path=file_path)
    file_exists, file_dict['id'] = get_file_status(sha256_hash=file_dict['sha256_hash'])
    if file_exists:
        raise FileExistsError(f"File already exists. File id: {file_dict['id']}")
    
    file_dict['extension'] = file_path.suffix.lstrip(".").lower()

    file_stats = file_path.stat()
    file_dict['size'] = file_stats.st_size
    pacific = ZoneInfo("America/Los_Angeles")

    modified_timestamp = file_stats.st_mtime
    modified_utc = datetime.fromtimestamp(timestamp=modified_timestamp, tz=timezone.utc)
    modified_utc_iso_format = modified_utc.isoformat()
    modified_pacific_iso_format = modified_utc.astimezone(tz=pacific).isoformat()

    birth_timestamp = file_stats.st_birthtime
    birth_utc = datetime.fromtimestamp(timestamp=birth_timestamp, tz=timezone.utc)
    birth_utc_iso_format = birth_utc.isoformat()
    birth_pacific_iso_format = birth_utc.astimezone(tz=pacific).isoformat()

    file_dict['inserted_ts'] = datetime.now().isoformat()

    if modified_timestamp > birth_timestamp:
        file_dict['created_ts'] = birth_utc_iso_format
    else:
        file_dict['created_ts'] = modified_utc_iso_format

    if description:
        file_dict['description'] = description
    
    print("File Dict:\n")
    pprint(file_dict)
    print(f"Modified pacific iso format: {modified_pacific_iso_format}")
    print(f"Birth pacific iso format: {birth_pacific_iso_format}")

    proceed_choice = input("Proceed with inserting file? [y/n]: ").strip().lower() in ("y", "yes", "true", "1")
    if not proceed_choice:
        return False
    
    json_file_path = generate_shard_path(kind_directory="files", id_int=file_dict['id'], extension="json")
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(file_dict, f, indent=4)

    hash_record = {
        "id": file_dict['id'],
        "sha256_hash": file_dict['sha256_hash']
    }
    with open(hashes_file_path, "a", encoding="utf-8") as f:
        json.dump(hash_record, f)
        f.write("\n")


def create_collection(name: str):
    ...