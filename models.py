from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column
from sqlalchemy.types import TEXT


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    sha256_hash: Mapped[str] = mapped_column(TEXT, primary_key=True)
    extension: Mapped[str] = mapped_column(TEXT, nullable=False)
    fs_created_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)

    parent_id: Mapped[str | None] = mapped_column(
        TEXT,
        ForeignKey("bundles.id"),
    )


class BundleFile(Base):
    __tablename__ = "bundle_files"

    bundle_id: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey("bundles.id"),
        primary_key=True,
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey("files.sha256_hash"),
        primary_key=True,
    )
    file_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)


class CollectionFile(Base):
    __tablename__ = "collection_files"

    collection_id: Mapped[str] = mapped_column(
        TEXT, ForeignKey("collections.id"), primary_key=True
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        TEXT, ForeignKey("files.sha256_hash"), primary_key=True
    )
    file_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
