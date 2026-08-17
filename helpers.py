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

from models import File, Directory, DirectoryFile, StorageDevice, StorageDeviceFile
from connection import Session

IGNORED_NAMES = {".DS_Store"}


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


def build_directory(name: str, parent_id: str | None) -> Directory:
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
class DirectoryNode:
    directory: Directory
    files: list[File] = field(default_factory=list)
    directory_files: list[DirectoryFile] = field(default_factory=list)
    children: list["DirectoryNode"] = field(default_factory=list)

    file_path_map: dict[str, Path] = field(default_factory=dict)


def build_directory_node(directory_path: Path, parent_id: str | None) -> DirectoryNode:
    directory = build_directory(directory_path.name, parent_id)
    directory_node = DirectoryNode(directory)

    for child_path in directory_path.iterdir():
        if should_ignore_path(child_path):
            continue

        if child_path.is_file():
            file = build_file(child_path)
            directory_file = build_directory_file(directory, file, child_path)

            directory_node.files.append(file)
            directory_node.directory_files.append(directory_file)
            directory_node.file_path_map[file.sha256_hash] = child_path

        elif child_path.is_dir():
            child_directory_node = build_directory_node(child_path, directory.id)
            directory_node.children.append(child_directory_node)

    return directory_node


## SESSIONERS


def _get_directory_from_id(directory_id: str, session: SessionType) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == directory_id))


def _get_directory_file_from_id(
    directory_file_id: str, session: SessionType
) -> DirectoryFile | None:
    return session.scalar(
        select(DirectoryFile).where(DirectoryFile.id == directory_file_id)
    )


def _move_directory(
    directory: Directory, destination_directory: Directory | None, session: SessionType
) -> None:
    if destination_directory is not None:
        directory.parent_id = destination_directory.id
    else:
        directory.parent_id = None
    session.add(directory)


def _move_directory_file(
    directory_file: DirectoryFile,
    destination_directory: Directory,
    session: SessionType,
) -> None:
    directory_file.directory_id = destination_directory.id
    session.add(directory_file)


class FilebaseService:
    def get_parent_directory(directory: Directory) -> Directory | None:
        with Session() as session:
            return session.scalar(
                select(Directory).where(Directory.id == directory.parent_id)
            )

    def get_child_directories(directory: Directory | None) -> list[Directory]:
        if directory is not None:
            directory_id = directory.id
        else:
            directory_id = None

        with Session() as session:
            return session.scalars(
                select(Directory).where(Directory.parent_id == directory_id)
            ).all()

    def get_directory_files(directory: Directory) -> list[DirectoryFile]:
        with Session() as session:
            return session.scalars(
                select(DirectoryFile).where(DirectoryFile.directory_id == directory.id)
            ).all()

    def generate_directory_path(directory: Directory | None) -> str:
        if directory is None:
            return "/"

        reverse_directory_list = [directory]

        with Session() as session:

            def append_parents(d: Directory):
                parent_directory = session.scalar(
                    select(Directory).where(Directory.id == d.parent_id)
                )
                if parent_directory is not None:
                    reverse_directory_list.append(parent_directory)
                    append_parents(parent_directory)
                else:
                    return

            append_parents(directory)

        directory_list = reversed(reverse_directory_list)
        return "/" + "/".join(directory.name for directory in directory_list)

    # WRITERS
    def rename_directory(directory: Directory, new_name: str) -> None:
        with Session() as session:
            with session.begin():
                directory.name = new_name
                session.add(directory)

    def rename_directory_file(directory_file: DirectoryFile, new_name: str) -> None:
        with Session() as session:
            with session.begin():
                directory_file.file_name = new_name
                session.add(directory_file)

    def move_directory(
        directory: Directory, destination_directory: Directory | None
    ) -> None:
        with Session() as session:
            with session.begin():
                _move_directory(directory, destination_directory, session)

    def move_directory_file(
        directory_file: DirectoryFile, destination_directory: Directory
    ) -> None:
        with Session() as session:
            with session.begin():
                _move_directory_file(directory_file, destination_directory, session)

    def create_directory(name: str, parent_id: str | None) -> None:
        with Session() as session:
            with session.begin():
                directory = build_directory(name, parent_id)
                session.add(directory)

    def cut_paste_directories(
        directory_ids: set[str], destination_directory: Directory
    ) -> None:
        with Session() as session:
            with session.begin():
                for d_id in directory_ids:
                    directory = _get_directory_from_id(d_id, session)
                    _move_directory(directory, destination_directory, session)

    def cut_paste_directory_files(
        directory_file_ids: set[str], destination_directory: Directory
    ) -> None:
        with Session() as session:
            with session.begin():
                for df_id in directory_file_ids:
                    directory_file = _get_directory_file_from_id(df_id, session)
                    _move_directory_file(directory_file, destination_directory, session)



"""
To seperate helpers that must have a session
passed to them that is in a transaction block,
maybe make a new class, add a suffix to their name,
some way to distinguish them.
"""
