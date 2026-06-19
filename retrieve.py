"""
This is a temporary seperate file, going to first work out the retrieve mechanics,
then add the function to main.
"""

from pathlib import Path
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
import shutil

from tabulate import tabulate
import typer
from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Bundle, FileBundle
from connection import Session
from hashlib import file_digest
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType


IGNORED_NAMES = {".DS_Store"}

TERMINAL_PATH = Path(TERMINAL_PATH_STR)
STORAGE_PATH = Path(STORAGE_PATH_STR)


def should_ignore_path(path: Path) -> bool:
    return path.name in IGNORED_NAMES


def datetime_to_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def get_current_time_str() -> str:
    return datetime_to_str(datetime.now(timezone.utc))


def get_file_modified_time_str(file_path: Path) -> str:
    modified_ts = file_path.stat().st_mtime
    modified_dt = datetime.fromtimestamp(modified_ts, tz=timezone.utc)
    return datetime_to_str(modified_dt)


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def create_file(file_path: Path) -> File:
    return File(
        id=str(uuid.uuid4()),
        sha256_hash=generate_sha256_hash(file_path=file_path),
        extension=file_path.suffix.lstrip(".").lower(),
        inserted_ts=get_current_time_str(),
        created_ts=get_file_modified_time_str(file_path=file_path),
    )


def create_bundle(bundle_path: Path, parent_id: str | None) -> Bundle:
    return Bundle(
        id=str(uuid.uuid4()),
        name=bundle_path.name,
        inserted_ts=get_current_time_str(),
        parent_id=parent_id,
    )


def create_file_bundle(file: File, bundle: Bundle, file_path: Path) -> FileBundle:
    return FileBundle(
        file_id=file.id,
        bundle_id=bundle.id,
        file_name=file_path.name,
        inserted_ts=get_current_time_str(),
    )



def load_bundle(bundle_id: str, session: SessionType):
    files: list[File] = []
    bundles: list[Bundle] = []
    file_bundles: list[FileBundle] = []


    bundle = session.scalar(select(Bundle).where(Bundle.id == bundle_id))
    if bundle is None:
        raise ValueError("Bundle not found")
    child_bundles = session.scalars(
        select(Bundle).where(Bundle.parent_id == bundle_id)
    ).all()
    child_files = session.scalars(
        select(File)
        .join(FileBundle, File.id == FileBundle.file_id)
        .where(FileBundle.bundle_id == bundle_id)
    ).all()

    child_file_bundles = session.scalars(
        select(FileBundle).where(FileBundle.bundle_id == bundle_id)
    ).all()

    bundles.append(bundle)
    files.extend(child_files)
    file_bundles.extend(child_file_bundles)

    for child_bundle in child_bundles:
        nested_files, nested_bundles, nested_file_bundles = load_bundle(bundle_id=child_bundle.id, session=session)
        files.extend(nested_files)
        bundles.extend(nested_bundles)
        file_bundles.extend(nested_file_bundles)
        
    return files, bundles, file_bundles







with Session() as session:
    files, bundles, file_bundles = load_bundle(bundle_id="37bf9253-eb95-4b45-964d-597f9a3e82fc", session=session)

    from pprint import pprint
    pprint(files)
    pprint(bundles)
    pprint(file_bundles)