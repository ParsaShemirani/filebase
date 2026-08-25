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

from env_vars import DATABASE_PATH_STR


engine = create_engine("sqlite:///" + DATABASE_PATH_STR, echo=False)
Session = sessionmaker(bind=engine)


def get_current_time_str() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def generate_uuid4_str() -> str:
    return str(uuid.uuid4())


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    sha256_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, init=False
    )


class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default_factory=generate_uuid4_str, init=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("directories.id"), nullable=True
    )
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, init=False
    )

    __table_args__ = (UniqueConstraint("parent_id", "name"),)


class DirectoryFile(Base):
    __tablename__ = "directory_files"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default_factory=generate_uuid4_str, init=False
    )
    directory_id: Mapped[str] = mapped_column(Text, ForeignKey("directories.id"))
    file_sha256_hash: Mapped[str] = mapped_column(
        Text, ForeignKey("files.sha256_hash"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(Text)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, init=False
    )

    __table_args__ = (UniqueConstraint("directory_id", "file_name"),)


class StorageDevice(Base):
    __tablename__ = "storage_devices"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default_factory=generate_uuid4_str, init=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, init=False
    )


class StorageDeviceFile(Base):
    __tablename__ = "storage_device_files"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default_factory=generate_uuid4_str, init=False
    )
    storage_device_id: Mapped[str] = mapped_column(
        Text, ForeignKey("storage_devices.id")
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        Text, ForeignKey("files.sha256_hash"), nullable=False
    )
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, init=False
    )

    __table_args__ = (UniqueConstraint("storage_device_id", "file_sha256_hash"),)


def db_session(f):
    @wraps(f)
    def inner(*args, session: SessionType | None = None, **kwargs):
        if session is not None:
            return f(*args, session, **kwargs)
        else:
            with Session() as session:
                with session.begin():
                    return f(*args, session, **kwargs)

    return inner


class DatabaseService:
    def get_directory_from_id(
        self, directory_id: str, session: SessionType
    ) -> Directory:
        directory = session.scalar(
            select(Directory).where(Directory.id == directory_id)
        )

        if directory is not None:
            return directory
        else:
            raise ValueError(f"Directory with id {directory_id} not found")

    def get_directory_file_from_id(
        self, directory_file_id: str, session: SessionType
    ) -> DirectoryFile:
        directory_file = session.scalar(
            select(DirectoryFile).where(DirectoryFile.id == directory_file_id)
        )

        if directory_file is not None:
            return directory_file
        else:
            raise ValueError(f"Directory file with id {directory_file_id} not found")

    def get_parent_directory(
        self, directory_id: str, session: SessionType
    ) -> Directory | None:
        directory = self.get_directory_from_id(directory_id, session)
        return session.scalar(
            select(Directory).where(Directory.id == directory.parent_id)
        )

    def get_child_directories(
        self, directory_id: str | None, session: SessionType
    ) -> list[Directory]:
        return session.scalars(
            select(Directory).where(Directory.parent_id == directory_id)
        ).all()

    def get_directory_files(
        self, directory_id: str | None, session: SessionType
    ) -> list[DirectoryFile]:
        if directory_id is not None:
            return session.scalars(
                select(DirectoryFile).where(DirectoryFile.directory_id) == directory_id
            ).all()
        else:
            return []

    def generate_directory_path(
        self, directory_id: str | None, session: SessionType
    ) -> str:
        if directory_id is None:
            return "/"

        directory = self.get_directory_from_id(directory_id, session)
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

    def rename_directory(
        self, directory_id: str, new_name: str, session: SessionType
    ) -> None:
        def the_action(directory_id: str, new_name: str, session: SessionType) -> None:
            directory = self.get_directory_from_id(directory_id, session)
            directory.name = new_name

        if session is not None:
            return the_action(directory_id, new_name, session)
        else:
            with Session() as session:
                with session.begin:
                    return the_action(directory_id, new_name, session)

    def rename_directory_file(
        self, directory_file_id: str, new_name: str, session: SessionType
    ) -> None:
        directory_file = self.get_directory_file_from_id(directory_file_id, session)
        directory_file.file_name = new_name

    def move_directory(
        self,
        directory_id: str,
        destination_directory_id: str | None,
        session: SessionType,
    ) -> None:
        directory = self.get_directory_from_id(directory_id, session)

        if destination_directory_id is not None:
            destination_directory = self.get_directory_from_id(
                destination_directory_id, session
            )
            directory.parent_id = destination_directory.id
        else:
            directory.parent_id = None

    def move_directory_file(
        self,
        directory_file_id: str,
        destination_directory_id: str,
        session: SessionType,
    ) -> None:
        directory_file = self.get_directory_file_from_id(directory_file_id, session)
        self.get_directory_from_id(destination_directory_id, session)
        directory_file.directory_id = destination_directory_id

    def cut_paste_directories(
        self,
        directory_ids: set[str],
        destination_directory_id: str | None,
        session: SessionType,
    ) -> None:
        for d_id in directory_ids:
            self.move_directory(d_id, destination_directory_id, session)

    def cut_paste_directory_files(
        self,
        directory_file_ids: set[str],
        destination_directory_id: str,
        session: SessionType,
    ) -> None:
        for df_id in directory_file_ids:
            self.move_directory_file(df_id, destination_directory_id, session)

    def create_directory(
        self, name: str, parent_id: str | None, session: SessionType
    ) -> None:
        directory = Directory(name, parent_id)
        session.add(directory)
