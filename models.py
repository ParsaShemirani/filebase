from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
    Integer,
    TEXT,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    Mapped,
    mapped_column,
)


ISO_FMT_Z = "%Y-%m-%dT%H:%M:%S%z"

def get_current_time_str() -> str:
    now = datetime.now(tz=timezone.utc)
    now_str = now.strftime(format=ISO_FMT_Z)
    return now_str


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    extension: Mapped[str] = mapped_column(TEXT, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_ts: Mapped[str] = mapped_column(TEXT, nullable=False)

    collection_id: Mapped[int | None] = mapped_column(ForeignKey("collections.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False, default_factory=get_current_time_str, init=False)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(TEXT, nullable=False)

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("collections.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False, default_factory=get_current_time_str, init=False)
