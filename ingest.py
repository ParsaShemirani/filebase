from pathlib import Path
import uuid

from models import File
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
    file = File(
        id=str(uuid.uuid4()),
        sha256_hash=generate_sha256_hash(file_path=file_path),
        extension=file_path.suffix.lstrip(".").lower(),
        inserted_ts=get_current_time_str(),
        created_ts=get_file_modified_time_str(file_path=file_path)
    )
    return file