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


### Sessioners


def _get_directory_from_id(directory_id: str, session: SessionType) -> Directory:
    directory = session.scalar(select(Directory).where(Directory.id == directory_id))

    if directory is not None:
        return directory
    else:
        raise ValueError(f"Directory with id {directory_id} not found")


def _get_directory_file_from_id(
    directory_file_id: str, session: SessionType
) -> DirectoryFile:
    directory_file = session.scalar(
        select(DirectoryFile).where(DirectoryFile.id == directory_file_id)
    )

    if directory_file is not None:
        return directory_file
    else:
        raise ValueError(f"Directory file with id {directory_file_id} not found")


def _move_directory(
    directory_id: str, destination_directory_id: str | None, session: SessionType
) -> None:
    directory = _get_directory_from_id(directory_id, session)

    if destination_directory_id is not None:
        destination_directory = _get_directory_from_id(
            destination_directory_id, session
        )
        directory.parent_id = destination_directory.id
    else:
        directory.parent_id = None


def _move_directory_file(
    directory_file_id: str,
    destination_directory_id: str,
    session: SessionType,
) -> None:
    directory_file = _get_directory_file_from_id(directory_file_id, session)
    _get_directory_from_id(destination_directory_id, session)
    directory_file.directory_id = destination_directory_id


class FilebaseService:
    @staticmethod
    def get_directory_from_id(directory_id: str) -> Directory:
        with Session() as session:
            return _get_directory_from_id(directory_id, session)
    @staticmethod
    def get_directory_file_from_id(directory_file_id: str) -> DirectoryFile:
        with Session() as session:
            return _get_directory_file_from_id(directory_file_id, session)
    @staticmethod
    def get_parent_directory(directory_id: str) -> Directory | None:
        with Session() as session:
            directory = _get_directory_from_id(directory_id, session)
            return session.scalar(
                select(Directory).where(Directory.id == directory.parent_id)
            )

    @staticmethod
    def get_child_directories(directory_id: str | None) -> list[Directory]:
        with Session() as session:
            return session.scalars(
                select(Directory).where(Directory.parent_id == directory_id)
            ).all()

    @staticmethod
    def get_directory_files(directory_id: str | None) -> list[DirectoryFile]:
        if directory_id is not None:
            with Session() as session:
                return session.scalars(
                    select(DirectoryFile).where(
                        DirectoryFile.directory_id == directory_id
                    )
                ).all()
        else:
            return []

    @staticmethod
    def generate_directory_path(directory_id: str | None) -> str:
        if directory_id is None:
            return "/"

        with Session() as session:
            directory = _get_directory_from_id(directory_id, session)
            reverse_directory_list = [directory]

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

    @staticmethod
    def rename_directory(directory_id: str, new_name: str) -> None:
        with Session() as session:
            with session.begin():
                directory = _get_directory_from_id(directory_id, session)
                directory.name = new_name

    @staticmethod
    def rename_directory_file(directory_file_id: str, new_name: str) -> None:
        with Session() as session:
            with session.begin():
                directory_file = _get_directory_file_from_id(directory_file_id, session)
                directory_file.file_name = new_name

    @staticmethod
    def move_directory(directory_id: str, destination_directory_id: str | None) -> None:
        with Session() as session:
            with session.begin():
                _move_directory(directory_id, destination_directory_id, session)

    @staticmethod
    def move_directory_file(
        directory_file_id: str, destination_directory_id: str
    ) -> None:
        with Session() as session:
            with session.begin():
                _move_directory_file(
                    directory_file_id, destination_directory_id, session
                )

    @staticmethod
    def create_directory(name: str, parent_id: str | None) -> None:
        with Session() as session:
            with session.begin():
                directory = build_directory(name, parent_id)
                session.add(directory)

    @staticmethod
    def cut_paste_directories(
        directory_ids: set[str], destination_directory_id: str | None
    ) -> None:
        with Session() as session:
            with session.begin():
                for d_id in directory_ids:
                    _move_directory(d_id, destination_directory_id, session)

    @staticmethod
    def cut_paste_directory_files(
        directory_file_ids: set[str], destination_directory_id: str
    ) -> None:
        with Session() as session:
            with session.begin():
                for df_id in directory_file_ids:
                    _move_directory_file(df_id, destination_directory_id, session)
