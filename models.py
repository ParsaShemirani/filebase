from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column
from sqlalchemy.types import TEXT


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    sha256_hash: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    extension: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_ts: Mapped[str | None] = mapped_column(TEXT)


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)

    parent_id: Mapped[str | None] = mapped_column(
        TEXT,
        ForeignKey("bundles.id"),
    )


class FileBundle(Base):
    __tablename__ = "file_bundles"

    file_id: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey("files.id"),
        primary_key=True,
    )
    bundle_id: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey("bundles.id"),
        primary_key=True,
    )
    file_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False)
