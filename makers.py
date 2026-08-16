import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
from textual import log

from models import File, Directory, DirectoryFile
from connection import Session
from env_vars import STORAGE_PATH_STR

IGNORED_NAMES = {".DS_Store"}

STORAGE_PATH = Path(STORAGE_PATH_STR)

def should_ignore_path(path: Path) -> bool:
    return path.name in IGNORED_NAMES


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def get_stats_json(file_path: Path) -> str:
    stats = file_path.stat()
    stats_dict = {
        name: getattr(stats, name) for name in dir(stats) if name.startswith("st_")
    }
    return json.dumps(stats_dict, indent=None)


def create_directory(name: str, parent_id: str | None) -> Directory:
    return Directory(
        id=str(uuid.uuid4()),
        name=name,
        parent_id=parent_id,
    )


def build_file(file_path: Path) -> File:
    return File(
        sha256_hash=generate_sha256_hash(file_path),
        size_bytes=file_path.stat().st_size,
    )


def build_directory_file(
    directory: Directory, file: File, file_path: Path
) -> DirectoryFile:
    return DirectoryFile(
        id=str(uuid.uuid4()),
        directory_id=directory.id,
        file_sha256_hash=file.sha256_hash,
        file_name=file_path.name,
        stats_json=get_stats_json(file_path),
    )


@dataclass
class DirectoryBuild:
    directories: list[Directory] = field(default_factory=list)
    files: list[File] = field(default_factory=list)
    directory_files: list[DirectoryFile] = field(default_factory=list)
    file_id_path_map: dict[str, Path] = field(default_factory=dict)


def build_directory(directory_path: Path, parent_id: str | None) -> DirectoryBuild:
    directory_build = DirectoryBuild()

    directory = create_directory(directory_path.name, parent_id)
    directory_build.directories.append(directory)

    for child_path in directory_path.iterdir():
        if should_ignore_path(child_path):
            continue

        if child_path.is_file():
            child_file = build_file(child_path)
            child_directory_file = build_directory_file(
                directory, child_file, child_path
            )

            directory_build.files.append(child_file)
            directory_build.directory_files.append(child_directory_file)
            directory_build.file_id_path_map[child_file.sha256_hash] = child_path

        elif child_path.is_dir():
            nested_directory_build = build_directory(child_path, directory.id)

            directory_build.directories.extend(nested_directory_build.directories)
            directory_build.files.extend(nested_directory_build.files)
            directory_build.directory_files.extend(
                nested_directory_build.directory_files
            )
            directory_build.file_id_path_map.update(
                nested_directory_build.file_id_path_map
            )

    return directory_build


def build_data_directory(directory: Directory, session: SessionType) -> DirectoryBuild:
    directory_build = DirectoryBuild()
    directory_build.directories.append(directory)

    child_directory_files = session.scalars(
        select(DirectoryFile).where(DirectoryFile.directory_id == directory.id)
    ).all()

    child_file_hashes = [cdf.file_sha256_hash for cdf in child_directory_files]
    child_files = session.scalars(
        select(File).where(File.sha256_hash.in_(child_file_hashes))
    )

    directory_build.directory_files.extend(child_directory_files)
    directory_build.files.extend(child_files)

    child_directories = session.scalars(
        select(Directory).where(Directory.parent_id == directory.id)
    ).all()
    for cd in child_directories:
        nested_directory_build = build_data_directory(cd, session)

        directory_build.directories.extend(nested_directory_build.directories)
        directory_build.files.extend(nested_directory_build.files)
        directory_build.directory_files.extend(nested_directory_build.directory_files)

    return directory_build

def retrieve_directory(directory_build: DirectoryBuild) -> None:
    ...