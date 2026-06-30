from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SessionType
from sqlalchemy.orm import sessionmaker

from env_vars import DATABASE_PATH_STR
from models import Directory, DirectoryFile, File


ROOT_ID = "root"
ORIGINAL_DATABASE_PATH = Path(DATABASE_PATH_STR).expanduser()
_active_database_path = ORIGINAL_DATABASE_PATH
_engine = create_engine("sqlite:///" + str(_active_database_path), echo=False)
Session = sessionmaker(bind=_engine)


@dataclass(frozen=True)
class BrowserItem:
    kind: str
    id: str
    name: str
    parent_id: str | None = None
    size_bytes: int | None = None
    sha256_hash: str | None = None


def utc_now_str() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def get_active_database_path() -> Path:
    return _active_database_path


def get_original_database_path() -> Path:
    return ORIGINAL_DATABASE_PATH


def use_database(database_path: Path) -> None:
    global Session, _active_database_path, _engine

    _engine.dispose()
    _active_database_path = database_path.expanduser()
    _engine = create_engine("sqlite:///" + str(_active_database_path), echo=False)
    Session = sessionmaker(bind=_engine)


def clone_database(source_path: Path | None = None) -> Path:
    source_path = source_path or ORIGINAL_DATABASE_PATH
    fd, temp_path_str = tempfile.mkstemp(prefix="filebase-edit-", suffix=".db")
    os.close(fd)
    temp_path = Path(temp_path_str)

    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        with sqlite3.connect(temp_path) as destination:
            source.backup(destination)
    return temp_path


def replace_database(replacement_path: Path, destination_path: Path | None = None) -> None:
    destination_path = destination_path or ORIGINAL_DATABASE_PATH
    _engine.dispose()
    os.replace(replacement_path, destination_path)


def normalize_directory_id(directory_id: str | None) -> str | None:
    return None if directory_id in (None, "", ROOT_ID) else directory_id


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Name is required.")
    if "/" in cleaned or "\\" in cleaned:
        raise ValueError("Names cannot contain path separators.")
    return cleaned


def get_directory_name(directory_id: str | None) -> str:
    directory_id = normalize_directory_id(directory_id)
    if directory_id is None:
        return "Root"
    with Session() as session:
        directory = require_directory(session, directory_id)
        return directory.name


def get_path(directory_id: str | None) -> str:
    directory_id = normalize_directory_id(directory_id)
    if directory_id is None:
        return "/"

    with Session() as session:
        names: list[str] = []
        current_id = directory_id
        while current_id is not None:
            directory = require_directory(session, current_id)
            names.append(directory.name)
            current_id = directory.parent_id
        return "/" + "/".join(reversed(names))


def get_parent_id(directory_id: str | None) -> str | None:
    directory_id = normalize_directory_id(directory_id)
    if directory_id is None:
        return None
    with Session() as session:
        return require_directory(session, directory_id).parent_id


def list_items(directory_id: str | None) -> list[BrowserItem]:
    directory_id = normalize_directory_id(directory_id)
    with Session() as session:
        if directory_id is not None:
            require_directory(session, directory_id)

        child_filter = (
            Directory.parent_id.is_(None)
            if directory_id is None
            else Directory.parent_id == directory_id
        )
        directories = session.scalars(
            select(Directory).where(child_filter).order_by(Directory.name)
        ).all()
        items = [
            BrowserItem("directory", directory.id, directory.name, directory.parent_id)
            for directory in directories
        ]

        if directory_id is None:
            return items

        file_rows = (
            session.query(DirectoryFile, File)
            .join(File, DirectoryFile.file_sha256_hash == File.sha256_hash)
            .filter(DirectoryFile.directory_id == directory_id)
            .order_by(DirectoryFile.file_name)
            .all()
        )
        items.extend(
            BrowserItem(
                "file",
                directory_file.file_name,
                directory_file.file_name,
                directory_id,
                file.size_bytes,
                file.sha256_hash,
            )
            for directory_file, file in file_rows
        )
        return items


def get_item_details(item: BrowserItem) -> list[tuple[str, str]]:
    with Session() as session:
        if item.kind == "directory":
            directory = require_directory(session, item.id)
            child_count = session.query(Directory).filter_by(
                parent_id=directory.id
            ).count()
            file_count = session.query(DirectoryFile).filter_by(
                directory_id=directory.id
            ).count()
            return [
                ("type", "directory"),
                ("name", directory.name),
                ("id", directory.id),
                ("parent", directory.parent_id or ROOT_ID),
                ("created", directory.inserted_ts),
                ("directories", str(child_count or 0)),
                ("files", str(file_count)),
            ]

        if item.kind == "file":
            if item.parent_id is None:
                raise ValueError("File items need a parent directory.")
            directory_file = require_directory_file(session, item.parent_id, item.id)
            file = session.get(File, directory_file.file_sha256_hash)
            return [
                ("type", "file"),
                ("name", directory_file.file_name),
                ("directory", directory_file.directory_id),
                ("sha256", directory_file.file_sha256_hash),
                ("size", str(file.size_bytes if file else "")),
                ("created", directory_file.inserted_ts),
            ]

    raise ValueError("Unknown item type.")


def create_directory(name: str, parent_id: str | None) -> str:
    name = validate_name(name)
    parent_id = normalize_directory_id(parent_id)
    with Session() as session:
        with session.begin():
            if parent_id is not None:
                require_directory(session, parent_id)
            if directory_name_exists(session, parent_id, name):
                raise ValueError("A directory with that name already exists there.")
            directory = Directory(
                id=str(uuid.uuid4()),
                name=name,
                inserted_ts=utc_now_str(),
                parent_id=parent_id,
            )
            session.add(directory)
        return directory.id


def rename_item(item: BrowserItem, new_name: str) -> None:
    new_name = validate_name(new_name)
    with Session() as session:
        with session.begin():
            if item.kind == "directory":
                directory = require_directory(session, item.id)
                if directory_name_exists(session, directory.parent_id, new_name, item.id):
                    raise ValueError("A directory with that name already exists there.")
                directory.name = new_name
                return

            if item.kind == "file":
                if item.parent_id is None:
                    raise ValueError("File items need a parent directory.")
                directory_file = require_directory_file(session, item.parent_id, item.id)
                if session.get(DirectoryFile, (item.parent_id, new_name)) is not None:
                    raise ValueError("A file with that name already exists here.")
                directory_file.file_name = new_name
                return

    raise ValueError("Unknown item type.")


def move_item(item: BrowserItem, destination_id: str | None) -> None:
    destination_id = normalize_directory_id(destination_id)
    with Session() as session:
        with session.begin():
            if destination_id is not None:
                require_directory(session, destination_id)

            if item.kind == "directory":
                move_directory(session, item.id, destination_id)
                return

            if item.kind == "file":
                if item.parent_id is None or destination_id is None:
                    raise ValueError("Files can only move between real directories.")
                move_file(session, item.parent_id, item.id, destination_id)
                return

    raise ValueError("Unknown item type.")


def move_items(items: list[BrowserItem], destination_id: str | None) -> None:
    destination_id = normalize_directory_id(destination_id)
    with Session() as session:
        with session.begin():
            if destination_id is not None:
                require_directory(session, destination_id)

            for item in items:
                if item.kind == "directory":
                    move_directory(session, item.id, destination_id)
                elif item.kind == "file":
                    if item.parent_id is None or destination_id is None:
                        raise ValueError("Files can only move between real directories.")
                    move_file(session, item.parent_id, item.id, destination_id)
                else:
                    raise ValueError("Unknown item type.")


def require_directory(session: SessionType, directory_id: str) -> Directory:
    directory = session.get(Directory, directory_id)
    if directory is None:
        raise ValueError("Directory not found.")
    return directory


def require_directory_file(
    session: SessionType, directory_id: str, file_name: str
) -> DirectoryFile:
    directory_file = session.get(DirectoryFile, (directory_id, file_name))
    if directory_file is None:
        raise ValueError("File not found in that directory.")
    return directory_file


def move_directory(
    session: SessionType, directory_id: str, new_parent_id: str | None
) -> None:
    directory = require_directory(session, directory_id)
    if directory.id == new_parent_id:
        raise ValueError("A directory cannot move into itself.")
    if new_parent_id is not None and is_descendant(session, new_parent_id, directory.id):
        raise ValueError("A directory cannot move into one of its children.")
    if directory_name_exists(session, new_parent_id, directory.name, directory.id):
        raise ValueError("A directory with that name already exists there.")
    directory.parent_id = new_parent_id


def move_file(
    session: SessionType,
    source_directory_id: str,
    file_name: str,
    destination_directory_id: str,
) -> None:
    if source_directory_id == destination_directory_id:
        return

    directory_file = require_directory_file(session, source_directory_id, file_name)
    if session.get(DirectoryFile, (destination_directory_id, file_name)) is not None:
        raise ValueError("A file with that name already exists in the destination.")

    session.delete(directory_file)
    session.flush()
    session.add(
        DirectoryFile(
            directory_id=destination_directory_id,
            file_name=file_name,
            file_sha256_hash=directory_file.file_sha256_hash,
            stats_json=directory_file.stats_json,
            inserted_ts=utc_now_str(),
        )
    )


def is_descendant(
    session: SessionType, directory_id: str, possible_ancestor_id: str
) -> bool:
    current_id: str | None = directory_id
    while current_id is not None:
        if current_id == possible_ancestor_id:
            return True
        directory = session.get(Directory, current_id)
        current_id = directory.parent_id if directory else None
    return False


def directory_name_exists(
    session: SessionType,
    parent_id: str | None,
    name: str,
    excluding_id: str | None = None,
) -> bool:
    parent_filter = (
        Directory.parent_id.is_(None)
        if parent_id is None
        else Directory.parent_id == parent_id
    )
    stmt = select(Directory.id).where(parent_filter, Directory.name == name)
    if excluding_id is not None:
        stmt = stmt.where(Directory.id != excluding_id)
    return session.scalar(stmt) is not None


def friendly_error(error: Exception) -> str:
    if isinstance(error, IntegrityError):
        return "That name already exists there."
    return str(error)
