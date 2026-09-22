from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from sqlalchemy import select

from db_funcs import Session
from models import Directory, DirectoryFile, File


BATCH_SIZE = 1000


def load_gold_hashes(path: Path) -> set[str]:
    with path.open() as f:
        return {line.strip() for line in f if line.strip()}


def normalize_stats_json(stats_json: str) -> str:
    return json.dumps(json.loads(stats_json), indent=None)


def iter_gold_source_rows(source_db_path: Path, gold_hashes: set[str]):
    with sqlite3.connect(source_db_path) as conn:
        cursor = conn.execute(
            "SELECT path, sha256_hash, stat_json FROM files WHERE sha256_hash IS NOT NULL"
        )
        for path_str, sha256_hash, stats_json in cursor:
            if sha256_hash in gold_hashes:
                yield Path(path_str), sha256_hash, normalize_stats_json(stats_json)


def strip_prefix(path: Path, prefix: Path | None) -> Path:
    if prefix is None:
        return path
    return path.relative_to(prefix)


def get_directory_parts(path: Path) -> tuple[str, ...]:
    return path.parent.parts[1:] if path.is_absolute() else path.parent.parts


def get_or_create_directory(session, parent_id: str | None, name: str) -> Directory:
    directory = session.scalar(
        select(Directory).where(
            Directory.parent_id == parent_id,
            Directory.name == name,
        )
    )
    if directory is None:
        directory = Directory(name=name, parent_id=parent_id)
        session.add(directory)
        session.flush()
    return directory


def get_or_create_directory_path(
    session,
    directory_cache: dict[tuple[str | None, str], Directory],
    parts: tuple[str, ...],
) -> Directory:
    directory = None
    parent_id = None

    for name in parts:
        key = (parent_id, name)
        directory = directory_cache.get(key)
        if directory is None:
            directory = get_or_create_directory(session, parent_id, name)
            directory_cache[key] = directory
        parent_id = directory.id

    if directory is None:
        raise ValueError("Gold file path has no parent directory")
    return directory


def insert_gold_files(
    source_db_path: Path,
    gold_files_path: Path,
    prefix: Path | None,
) -> int:
    gold_hashes = load_gold_hashes(gold_files_path)
    directory_cache: dict[tuple[str | None, str], Directory] = {}
    count = 0

    with Session() as session:
        for source_path, sha256_hash, stats_json in iter_gold_source_rows(
            source_db_path,
            gold_hashes,
        ):
            import_path = strip_prefix(source_path, prefix)
            stats = json.loads(stats_json)
            directory = get_or_create_directory_path(
                session,
                directory_cache,
                get_directory_parts(import_path),
            )

            if session.get(File, sha256_hash) is None:
                session.add(
                    File(
                        sha256_hash=sha256_hash,
                        size_bytes=stats["st_size"],
                    )
                )

            directory_file = session.scalar(
                select(DirectoryFile).where(
                    DirectoryFile.directory_id == directory.id,
                    DirectoryFile.file_name == import_path.name,
                )
            )
            if directory_file is None:
                session.add(
                    DirectoryFile(
                        directory_id=directory.id,
                        file_sha256_hash=sha256_hash,
                        file_name=import_path.name,
                        stats_json=stats_json,
                    )
                )

            count += 1
            if count % BATCH_SIZE == 0:
                session.commit()

        session.commit()

    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import selected source DB file paths into the filebase DB."
    )
    parser.add_argument("source_db", type=Path)
    parser.add_argument("gold_files", type=Path)
    parser.add_argument("--strip-prefix", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = insert_gold_files(
        source_db_path=args.source_db,
        gold_files_path=args.gold_files,
        prefix=args.strip_prefix,
    )
    print(f"Imported {count} gold file paths")


if __name__ == "__main__":
    main()
