from sqlalchemy import Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    sha256_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(Text, nullable=False)


class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("directories.id"), nullable=True
    )

    __table_args__ = UniqueConstraint("parent_id", "name")


class DirectoryFile(Base):
    __tablename__ = "directory_files"

    directory_id: Mapped[str] = mapped_column(
        Text, ForeignKey("directories.id"), primary_key=True
    )
    file_name: Mapped[str] = mapped_column(Text, primary_key=True)
    file_sha256_hash: Mapped[str] = mapped_column(
        Text, ForeignKey("files.sha256_hash"), nullable=False
    )
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)
    inserted_ts: Mapped[str] = mapped_column(Text, nullable=False)
