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
    relationship,
)


ISO_FMT_Z = "%Y-%m-%dT%H:%M:%S%z"

def get_current_time_str() -> str:
    now = datetime.now(tz=timezone.utc)
    now_str = now.strftime(format=ISO_FMT_Z)
    return now_str


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, init=False
    )
    type: Mapped[str] = mapped_column(TEXT, init=False)

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

    # Default
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False, default_factory=get_current_time_str, init=False)

    # Joined table inheritance
    __mapper_args__ = {"polymorphic_identity": "node", "polymorphic_on": "type"}


class Edge(Base):
    __tablename__ = "edges"

    source_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), primary_key=True, init=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), primary_key=True, init=False)
    type: Mapped[str] = mapped_column(TEXT, primary_key=True)

    # Node relationships
    source_node: Mapped[Node] = relationship(
        "Node",
        foreign_keys=[source_id],
        back_populates="outgoing_relationships",
        repr=False,
        #init=False,
    )
    target_node: Mapped[Node] = relationship(
        "Node",
        foreign_keys=[target_id],
        back_populates="incoming_relationships",
        repr=False,
        #init=False,
    )

    # Default
    inserted_ts: Mapped[str] = mapped_column(TEXT, nullable=False, default_factory=get_current_time_str, init=False)


class File(Node):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    extension: Mapped[str] = mapped_column(TEXT)
    size: Mapped[int] = mapped_column(Integer)
    created_ts: Mapped[str] = mapped_column(TEXT)

    __mapper_args__ = {"polymorphic_identity": "file"}


class StorageDevice(Node):
    __tablename__ = "storage_devices"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(TEXT)
    size: Mapped[int] = mapped_column(Integer)
    path: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    __mapper_args__ = {"polymorphic_identity": "storage_device"}


class Description(Node):
    __tablename__ = "descriptions"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    text: Mapped[str] = mapped_column(TEXT, unique=True)

    __mapper_args__ = {"polymorphic_identity": "description"}


class Collection(Node):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(TEXT, unique=True)

    __mapper_args__ = {"polymorphic_identity": "collection"}
