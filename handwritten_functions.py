import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import asdict

from sqlalchemy.orm import Session as SessionType

from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Directory, DirectoryFile
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
        size_bytes=file_path.stat().st_size,
        inserted_ts=get_current_time_str(),
    )

def create_directory(name: str, parent_id: str | None) -> Directory:
    return Directory(
        id=str(uuid.uuid4()),
        name=name,
        inserted_ts=get_current_time_str(),
        parent_id=parent_id,
    )

def create_directory_file(directory: Directory, file: File, file_path: Path) -> DirectoryFile:
    return DirectoryFile(
        directory_id=directory.id,
        file_name=file_path.name,
        file_sha256_hash=file.sha256_hash,
        stats_json=get_stats_json(file_path=file_path),
        inserted_ts=get_current_time_str(),
    )

def build_directory(directory_path: Path, parent_id: str | None) -> tuple[list[File], list[Directory], list[DirectoryFile], dict[str, Path]]:
    files: list[File] = []
    directories: list[Directory] = []
    directory_files: list[DirectoryFile] = []
    file_path_dict: dict[str, Path] = {}

    directory = create_directory(name=directory_path.name, parent_id=parent_id)
    directories.append(directory)

    for child_path in directory_path.iterdir():
        if should_ignore_path(path=child_path):
            continue

        if child_path.is_file():
            child_file = create_file(file_path=child_path)
            child_directory_file = create_directory_file(directory=directory,file=child_file,file_path=child_path)
            files.append(child_file)
            directory_files.append(child_directory_file)
            file_path_dict[child_file.sha256_hash] = child_path

        elif child_path.is_dir():
            nested_files, nested_directories, nested_directory_files, nested_file_path_dict = build_directory(directory_path=child_path, parent_id=directory.id)
            files.extend(nested_files)
            directories.extend(nested_directories)
            directory_files.extend(nested_directory_files)
            file_path_dict.update(nested_file_path_dict)
        
        return files, directories, directory_files, file_path_dict