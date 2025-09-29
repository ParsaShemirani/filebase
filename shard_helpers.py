from pathlib import Path

from settings import json_database_directory


def generate_shard_path(kind: str, id_int: int, extension: str) -> Path:
    """
    Creates a sharded directory layout.
    Max 9,801 files. 99 Directories
    each containing 99 files. Directory name
    is hundreds count of the number.
    """
    hundreds = id_int // 100
    shard_ending = Path(f"{kind}/{hundreds}/{id_int}.{extension}")
    shard_path = json_database_directory / shard_ending

    # Ensure parent directory exists
    shard_path.parent.mkdir(exist_ok=True)
    return shard_path
