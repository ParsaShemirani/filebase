from __future__ import annotations

import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import dataclass, field
from functools import wraps

from sqlalchemy import (
    Text,
    Integer,
    ForeignKey,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    sessionmaker,
    DeclarativeBase,
    MappedAsDataclass,
    Mapped,
    Session as SessionType,
    mapped_column,
)

from models import File, Directory, DirectoryFile
from env_vars import DATABASE_PATH_STR


engine = create_engine("sqlite:///" + DATABASE_PATH_STR, echo=False)
Session = sessionmaker(bind=engine)


def db_session(*, transaction: bool):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, session: SessionType | None = None, **kwargs):
            if session is not None:
                return f(*args, session=session, **kwargs)
            else:
                with Session() as session:
                    if transaction:
                        with session.begin():
                            return f(*args, session=session, **kwargs)
                    else:
                        return f(*args, session=session, **kwargs)

        return wrapper

    return decorator


class DatabaseService:
    @db_session(transaction=False)
    def get_directory_from_id(
        self, directory_id: str, *, session: SessionType
    ) -> Directory:
        directory = session.get(Directory, directory_id)

        if directory is not None:
            return directory
        else:
            raise ValueError(f"Directory with id {directory_id} not found")

    @db_session(transaction=False)
    def get_directory_file_from_id(
        self, directory_file_id: str, *, session: SessionType
    ) -> DirectoryFile:
        directory_file = session.get(DirectoryFile, directory_file_id)

        if directory_file is not None:
            return directory_file
        else:
            raise ValueError(f"Directory file with id {directory_file_id} not found")

    @db_session(transaction=False)
    def get_parent_directory(
        self, directory_id: str, *, session: SessionType
    ) -> Directory | None:
        directory = self.get_directory_from_id(directory_id, session=session)

        if directory.parent_id is None:
            return None
        else:
            return session.get(Directory, directory.parent_id)

    @db_session(transaction=False)
    def get_child_directories(
        self, directory_id: str | None, *, session: SessionType
    ) -> list[Directory]:
        if directory_id is not None:
            self.get_directory_from_id(directory_id, session=session)
        return session.scalars(
            select(Directory).where(Directory.parent_id == directory_id)
        ).all()

    @db_session(transaction=False)
    def get_directory_files(
        self, directory_id: str, *, session: SessionType
    ) -> list[DirectoryFile]:
        self.get_directory_from_id(directory_id, session=session)
        return session.scalars(
            select(DirectoryFile).where(DirectoryFile.directory_id == directory_id)
        ).all()

    @db_session(transaction=False)
    def generate_directory_path(
        self, directory_id: str | None, *, session: SessionType
    ) -> str:
        if directory_id is None:
            return "/"

        directory = self.get_directory_from_id(directory_id, session=session)
        reverse_directory_list = [directory]

        def append_parents(d: Directory):
            parent_directory = session.get(Directory, d.parent_id)
            if parent_directory is not None:
                reverse_directory_list.append(parent_directory)
                append_parents(parent_directory)
            else:
                return

        append_parents(directory)

        directory_list = reversed(reverse_directory_list)
        return "/" + "/".join(d.name for d in directory_list)

    # WRITERS

    @db_session(transaction=True)
    def rename_directory(
        self, directory_id: str, new_name: str, *, session: SessionType
    ) -> None:
        directory = self.get_directory_from_id(directory_id, session=session)
        directory.name = new_name

    @db_session(transaction=True)
    def rename_directory_file(
        self, directory_file_id: str, new_name: str, *, session: SessionType
    ) -> None:
        directory_file = self.get_directory_file_from_id(
            directory_file_id, session=session
        )
        directory_file.file_name = new_name

    @db_session(transaction=True)
    def move_directory(
        self,
        directory_id: str,
        destination_directory_id: str | None,
        *,
        session: SessionType,
    ) -> None:
        directory = self.get_directory_from_id(directory_id, session=session)

        if destination_directory_id is not None:
            self.get_directory_from_id(destination_directory_id, session=session)
            directory.parent_id = destination_directory_id
        else:
            directory.parent_id = None

    @db_session(transaction=True)
    def move_directory_file(
        self,
        directory_file_id: str,
        destination_directory_id: str,
        *,
        session: SessionType,
    ) -> None:
        directory_file = self.get_directory_file_from_id(
            directory_file_id, session=session
        )
        self.get_directory_from_id(destination_directory_id, session=session)
        directory_file.directory_id = destination_directory_id

    @db_session(transaction=True)
    def cut_paste_directories(
        self,
        directory_ids: set[str],
        destination_directory_id: str | None,
        *,
        session: SessionType,
    ) -> None:
        for d_id in directory_ids:
            self.move_directory(d_id, destination_directory_id, session=session)

    @db_session(transaction=True)
    def cut_paste_directory_files(
        self,
        directory_file_ids: set[str],
        destination_directory_id: str,
        *,
        session: SessionType,
    ) -> None:
        for df_id in directory_file_ids:
            self.move_directory_file(df_id, destination_directory_id, session=session)
