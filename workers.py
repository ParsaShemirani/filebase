import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
from textual import log

from models import Directory, DirectoryFile

IGNORED_NAMES = {".DS_Store"}

### READERS


def get_directory_from_id(id: str, session: SessionType) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == id))


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


### WRITERS


def rename_directory(directory: Directory, new_name: str, session: SessionType) -> None:
    directory.name = new_name
    session.add(directory)
    session.commit()
