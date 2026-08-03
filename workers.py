import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType

from models import Directory, DirectoryFile

IGNORED_NAMES = {".DS_Store"}

def get_directory_from_id(id: str, session: SessionType) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == id))

def get_root_directories(session: SessionType) -> list[Directory]:
    return session.scalars(select(Directory).where(Directory.parent_id == None)).all()

def get_parent_directory(
    directory: Directory, session: SessionType
) -> Directory | None:
    return session.scalar(select(Directory).where(Directory.id == directory.parent_id))


def get_child_directories(
    directory: Directory, session: SessionType
) -> list[Directory]:
    return session.scalars(
        select(Directory).where(Directory.parent_id == directory.id)
    ).all()


def get_child_directory_files(
    directory: Directory, session: SessionType
) -> list[DirectoryFile]:
    return session.scalars(
        select(DirectoryFile).where(DirectoryFile.directory_id == directory.id)
    ).all()
