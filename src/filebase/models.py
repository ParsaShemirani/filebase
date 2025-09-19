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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector

class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False
    )
    type: Mapped[str] = mapped_column(String(30), init=False)
    inserted_ts: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), init=False
    )

    # Edge relationships
    outgoing_relationships: Mapped[list[Edge]] = relationship(
        "Edge",
        foreign_keys="Edge.source_id",
        back_populates="source_node",
        repr=False,
        init=False,
    )
    incoming_relationships: Mapped[list[Edge]] = relationship(
        "Edge",
        foreign_keys="Edge.target_id",
        back_populates="target_node",
        repr=False,
        init=False,
    )

    # Joined table inheritance
    __mapper_args__ = {"polymorphic_identity": "node", "polymorphic_on": "type"}


class Edge(Base):
    __tablename__ = "edges"

    source_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True
    )
    type: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Node relationships
    source_node: Mapped[Node] = relationship(
        "Node",
        foreign_keys=[source_id],
        back_populates="outgoing_relationships",
        repr=False,
        init=False,
    )
    target_node: Mapped[Node] = relationship(
        "Node",
        foreign_keys=[target_id],
        back_populates="incoming_relationships",
        repr=False,
        init=False,
    )

    # Default
    inserted_ts: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), init=False
    )


class File(Node):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    root_name: Mapped[str] = mapped_column(String(160))
    version_number: Mapped[int] = mapped_column(Integer)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    extension: Mapped[str] = mapped_column(String(16))
    size: Mapped[int] = mapped_column(BigInteger)
    created_ts: Mapped[datetime] = mapped_column(DateTime)
    specific_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=None
    )

    __mapper_args__ = {"polymorphic_identity": "file"}


class StorageDevice(Node):
    __tablename__ = "storage_devices"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(String(160))
    size: Mapped[int] = mapped_column(BigInteger)
    path: Mapped[str | None] = mapped_column(String(160), default=None, unique=True)

    __mapper_args__ = {"polymorphic_identity": "storage_device"}


class Description(Node):
    __tablename__ = "descriptions"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    text: Mapped[str] = mapped_column(Text, unique=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), repr=False)
    tsv: Mapped[str] = mapped_column(TSVECTOR, Computed("to_tsvector('english', coalesce(text, ''))", persisted=True), init=False)

    __mapper_args__ = {"polymorphic_identity": "description"}


class Collection(Node):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(String(160), unique=True)

    __mapper_args__ = {"polymorphic_identity": "collection"}


class VersionGroup(Node):
    __tablename__ = "version_groups"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )

    __mapper_args__ = {"polymorphic_identity": "version_group"}
