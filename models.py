from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    Mapped,
    mapped_column,
    relationship,
)

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class File(Base):
    __tablename__ = "files"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    inserted_ts: Mapped[str] = mapped_column(Text)

    sha256_hash: Mapped[str] = mapped_column(Text, unique=True)
    extension: Mapped[str] = mapped_column(Text)
    created_ts: Mapped[str] = mapped_column(Text)

    collection_id: Mapped[int | None] = mapped_column(ForeignKey("collections.id"), nullable=True)
    collection: Mapped[Collection | None] = relationship(back_populates="files", init=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    inserted_ts: Mapped[str] = mapped_column(Text)

    files: Mapped[list[File]] = relationship(back_populates="collection", init=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)


