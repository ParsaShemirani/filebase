from pathlib import Path
import uuid

from models import File, Bundle, FileBundle
from connection import Session
from hashlib import file_digest

from datetime import datetime, timezone

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
        created_ts=get_file_modified_time_str(file_path=file_path)
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

def build_bundle(bundle_path: Path, parent_id: str | None):
    bundle = create_bundle(bundle_path=bundle_path, parent_id=parent_id)

    files = []
    file_bundles = []
    for item in bundle_path.iterdir():
        if item.is_file():
            file = create_file(file_path=item)
            files.append(file)
            file_bundle = create_file_bundle(file=file, bundle=bundle, file_path=item)
            file_bundles.append(file_bundle)
        elif item.is_dir():
            print("DIR :", item.name)
    return files, file_bundles

def main():
    bundle_path = Path("/Users/parsahome/Desktop/project_storage_daniel_james")
    bundle = Bundle(
        id=str(uuid.uuid4()),
        name=bundle_path.name,
        inserted_ts=get_current_time_str(),
        parent_id=None
    )
