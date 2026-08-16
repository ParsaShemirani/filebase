import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
from textual import log

from models import Directory, DirectoryFile
from makers import create_directory

### READERS


def get_directory_from_id(id: str, session: SessionType) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == id))

def get_directory_file_from_id(id: str, session: SessionType) -> DirectoryFile | None:
    return session.scalar(select(DirectoryFile).where(DirectoryFile.id == id))

def get_parent_directory(
    directory: Directory, session: SessionType
) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == directory.parent_id))


def get_child_directories(
    directory: Directory | None, session: SessionType
) -> list[Directory]:
    if directory is not None:
        directory_id = directory.id
    else:
        directory_id = None
    return session.scalars(
        select(Directory).where(Directory.parent_id == directory_id)
    ).all()


def get_directory_files(
    directory: Directory, session: SessionType
) -> list[DirectoryFile]:
    return session.scalars(
        select(DirectoryFile).where(DirectoryFile.directory_id == directory.id)
    ).all()

def generate_directory_path_str(directory: Directory | None, session: SessionType) -> str:
    if directory is None:
        return "/"

    reverse_directory_list = [directory]

    def append_parents(directory: Directory):
        parent_directory = session.scalar(select(Directory).where(Directory.id == directory.parent_id))
        if parent_directory is not None:
            reverse_directory_list.append(parent_directory)
            append_parents(parent_directory)
        else:
            return
    append_parents(directory)

    directory_list = reversed(reverse_directory_list)
    return "/" + "/".join(directory.name for directory in directory_list)


### WRITERS


def rename_directory(directory: Directory, new_name: str, session: SessionType) -> None:
    directory.name = new_name
    session.add(directory)
    session.commit()

def rename_directory_file(directory_file: DirectoryFile, new_name: str, session: SessionType) -> None:
    directory_file.file_name = new_name
    session.add(directory_file)
    session.commit()

def move_directory(directory: Directory, new_parent_directory: Directory | None, session: SessionType) -> None:
    if new_parent_directory is not None:
        directory.parent_id = new_parent_directory.id
    else:
        directory.parent_id = None
    session.add(directory)
    session.commit()

def move_directory_file(directory_file: DirectoryFile, new_directory: Directory, session: SessionType) -> None:
    directory_file.directory_id = new_directory.id
    session.add(directory_file)
    session.commit()

def insert_directory(name: str, parent_id: str | None, session) -> None:
    directory = create_directory(name, parent_id)
    session.add(directory)
    session.commit()

    "FIX SAG CREATE DIRECTORY WHTAT IS CREWATE BUILD WRITE MOVED"