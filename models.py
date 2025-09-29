from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from dataclasses import field

from sqlalchemy import (
    Index,
    Computed,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    CHAR,
    Text,
    DateTime,
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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, init=False)
    sha256_hash: Mapped[int] = mapped_column(CHAR(64), unique=True)
    extension: Mapped[str] = mapped_column(String())
    size: Mapped[int] = mapped_column(BigInteger)
    created_ts: Mapped[datetime] = mapped_column(DateTime)
    inserted_ts: Mapped[datetime] = mapped_column(DateTime)

class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, init=False)



class StorageDevice(Base):
    __tablename__ = "storage_devices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(String())
    size: Mapped[int] = mapped_column(BigInteger)

class Description