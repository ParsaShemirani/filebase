from datetime import datetime, timezone

from sqlalchemy import Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column


def get_current_time_str() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    sha256_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, default=None
    )


class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("directories.id"), nullable=True
    )
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, default=None
    )

    __table_args__ = (UniqueConstraint("parent_id", "name"),)


class DirectoryFile(Base):
    __tablename__ = "directory_files"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    directory_id: Mapped[str] = mapped_column(Text, ForeignKey("directories.id"))
    file_sha256_hash: Mapped[str] = mapped_column(
        Text, ForeignKey("files.sha256_hash"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(Text)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, default=None
    )

    __table_args__ = (UniqueConstraint("directory_id", "file_name"),)


class StorageDevice(Base):
    __tablename__ = "storage_devices"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, default=None
    )

class StorageDeviceFile(Base):
    __tablename__ = "storage_device_files"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storage_device_id: Mapped[str] = mapped_column(
        Text, ForeignKey("storage_devices.id")
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        Text, ForeignKey("files.sha256_hash"), nullable=False
    )
    origin_file_path: Mapped[str] = mapped_column(Text, nullable=True)
    inserted_ts: Mapped[str] = mapped_column(
        Text, nullable=False, insert_default=get_current_time_str, default=None
    )

    __table_args__ = (UniqueConstraint("storage_device_id", "file_sha256_hash"),)
