"""Functions that provide the entry point for files into the filebase

Functions are defined to ingest a file with the universal metadata,
and build on top of that to automate common workflows, such as ingesting
a file with an added description, file as part of collection, etc.
"""

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from hashlib import file_digest
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType, aliased

from filebase.connection import Session
from filebase.models import (
    Node,
    Edge,
    File,
    StorageDevice,
    VersionGroup,
    Description,
)
from filebase.lang_func import generate_embedding
from filebase.settings import intake_storage_device_path


FILENAME_REGEX = r"^(?P<root_name>.+)-v(?P<version_number>\d+)-(?P<sha256_hash>[0-9a-fA-F]{64})(?:\.(?P<extension>.+))$"


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


class FilenameComponents(NamedTuple):
    """Stores filename components from FILENAME_REGEX pattern"""

    root_name: str
    version_number: int
    sha256_hash: str


def extract_filename_components(filename: str) -> FilenameComponents | None:
    match = re.match(pattern=FILENAME_REGEX, string=filename)
    if match:
        filename_components = FilenameComponents(
            root_name=match.group("root_name"),
            version_number=int(match.group("version_number")),
            sha256_hash=match.group("sha256_hash"),
        )
        return filename_components
    else:
        return None


def generate_new_filename(
    root_name: str, version_number: int, sha256_hash: str, extension: str
) -> str:
    stem = f"{root_name}-v{version_number}-{sha256_hash}"
    if extension == "":
        new_filename = stem
    else:
        new_filename = stem + "." + extension
    return new_filename


def handle_version_group(
    session: SessionType, file: File, previous_sha256_hash: str
) -> None:
    # NEEDS REVISION BIG TIME
    F = aliased(File, flat=True)
    version_group = session.scalar(
        select(VersionGroup)
        .select_from(F)
        .join(Edge, Edge.source_id == F.id)
        .join(VersionGroup, VersionGroup.id == Edge.target_id)
        .where(F.sha256_hash == previous_sha256_hash, Edge.type == "in_version_group")
    )
    previous_file = session.scalar(
        select(File).where(File.sha256_hash == previous_sha256_hash)
    )

    if version_group is None:
        if previous_file.version_number != 1:
            raise ValueError("Houston, we have a problem")
        version_group = VersionGroup()
        previous_file_version_edge = Edge(
            source_id=previous_file.id,
            target_id=version_group.id,
            type="in_version_group",
        )
        session.add_all([version_group, previous_file_version_edge])

    file.version_number = previous_file.version_number + 1
    file_version_edge = Edge(
        source_id=file.id, target_id=version_group.id, type="in_version_group"
    )
    session.add(file_version_edge)


def associate_description(
    session: SessionType, node: Node, text: str, embedding: list[float]
) -> None:
    description = Description(text=text, embedding=embedding)
    edge = Edge(source_id=node.id, target_id=description.id, type="has_description")
    session.add_all([description, edge])


def associate_intake_storage_device(session: SessionType, file: File) -> None:
    intake_storage_device_id = session.scalar(
        select(StorageDevice.id).where(
            StorageDevice.path == str(intake_storage_device_path)
        )
    )
    edge = Edge(
        source_id=file.id,
        target_id=intake_storage_device_id,
        type="stored_on",
    )
    session.add(edge)


def create_file(
    session: SessionType,
    file_path: Path,
    created_ts: datetime | None,
) -> File:
    filename_components = extract_filename_components(filename=file_path.name)
    if filename_components:
        root_name = filename_components.root_name
        previous_sha256_hash = filename_components.sha256_hash
        # Following version number slightly more reliable
        # than the one from file components
        version_number = (
            session.scalar(
                select(File.version_number).where(
                    File.sha256_hash == previous_sha256_hash
                )
            )
            + 1
        )
    else:
        root_name = file_path.stem
        previous_sha256_hash = None
        version_number = 1

    sha256_hash = generate_sha256_hash(file_path=file_path)
    size = file_path.stat().st_size
    extension = file_path.suffix.lstrip(".").lower()
    if created_ts is None:
        created_ts = datetime.now(tz=timezone.utc)

    file = File(
        root_name=root_name,
        version_number=version_number,
        sha256_hash=sha256_hash,
        extension=extension,
        size=size,
        created_ts=created_ts,
    )
    session.add(file)
    return file


def ingest_file(
    file_path: Path,
    created_ts: datetime | None,
    description_text: str | None = None,
) -> None:
    with Session() as session:
        with session.begin():
            file = create_file(
                session=session, file_path=file_path, created_ts=created_ts
            )

            # Handling version number
            filename_components = extract_filename_components(filename=file_path.name)
            if filename_components:
                handle_version_group(
                    session=session,
                    file=file,
                    previous_sha256_hash=filename_components.sha256_hash,
                )

            # Creating / associating description
            if description_text:
                associate_description(
                    session=session,
                    node=file,
                    text=description_text,
                    embedding=generate_embedding(text=description_text),
                )

            associate_intake_storage_device(session=session, file=file)

        shutil.move(
            src=str(file_path), dst=str(intake_storage_device_path / file.sha256_hash)
        )
