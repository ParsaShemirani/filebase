from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column
from sqlalchemy.types import TEXT


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    sha256_hash: Mapped[str] = mapped_column(TEXT, primary_key=True)
    extension: Mapped[str] = mapped_column(TEXT, nullable=False)
    stats_json: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
    name: Mapped[str | None] = mapped_column(TEXT, nullable=True)


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class BundleFile(Base):
    __tablename__ = "bundle_files"

    bundle_id: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey("bundles.id"),
        primary_key=True,
    )
    path: Mapped[str] = mapped_column(TEXT, primary_key=True)
    file_sha256_hash: Mapped[str] = mapped_column(
        TEXT, ForeignKey("files.sha256_hash"), nullable=False
    )
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(TEXT, ForeignKey("directories.id"), nullable=True)


class DirectoryFile(Base):
    __tablename__ = "directory_files"

    directory_id: Mapped[str] = mapped_column(
        TEXT, ForeignKey("directories.id"), primary_key=True
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        TEXT, ForeignKey("files.sha256_hash"), primary_key=True
    )
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class DirectoryBundle(Base):
    __tablename__ = "directory_bundles"

    directory_id: Mapped[str] = mapped_column(
        TEXT, ForeignKey("directories.id"), primary_key=True
    )
    bundle_id: Mapped[str] = mapped_column(
        TEXT, ForeignKey("bundles.id"), primary_key=True
    )
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
