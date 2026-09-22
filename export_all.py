#!/usr/bin/env python3
"""Export every Filebase collection and bundle from content-addressed storage."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATABASE = Path("/Users/parsahome/filebase/filebase.db")
DEFAULT_STORAGE = Path("/Users/parsahome/filebase/storage")
DEFAULT_OUTPUT = Path("/Users/parsahome/filebase/export")


class ExportError(RuntimeError):
    """Raised when the database cannot be exported safely."""


@dataclass(frozen=True)
class Bundle:
    id: str
    name: str
    parent_id: str | None


def safe_name(value: str, kind: str) -> str:
    """Return a database name only if it is one safe path component."""
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ExportError(f"unsafe {kind} name in database: {value!r}")
    return value


def available_directory_name(name: str, object_id: str, used: set[str]) -> str:
    """Keep readable names, adding an id only when names collide."""
    candidate = safe_name(name, "directory")
    if candidate in used:
        candidate = f"{candidate}__{object_id}"
    if candidate in used:
        raise ExportError(f"duplicate output directory name: {candidate!r}")
    used.add(candidate)
    return candidate


class Exporter:
    def __init__(
        self,
        database: Path,
        storage: Path,
        output: Path,
        *,
        dry_run: bool,
        overwrite: bool,
    ) -> None:
        self.database = database
        self.storage = storage
        self.output = output
        self.dry_run = dry_run
        self.overwrite = overwrite
        self.files_exported = 0
        self.bytes_exported = 0

    def run(self) -> None:
        if not self.database.is_file():
            raise ExportError(f"database not found: {self.database}")
        if not self.storage.is_dir():
            raise ExportError(f"storage directory not found: {self.storage}")

        uri = f"file:{self.database.resolve()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            self._validate_schema(connection)
            collections = connection.execute(
                "SELECT id, name FROM collections ORDER BY inserted_ts, id"
            ).fetchall()
            bundle_rows = connection.execute(
                "SELECT id, name, parent_id FROM bundles ORDER BY inserted_ts, id"
            ).fetchall()
            bundles = {
                row["id"]: Bundle(row["id"], row["name"], row["parent_id"])
                for row in bundle_rows
            }
            self._validate_bundle_tree(bundles)

            self._make_directory(self.output)
            collections_dir = self.output / "collections"
            bundles_dir = self.output / "bundles"
            self._make_directory(collections_dir)
            self._make_directory(bundles_dir)

            used_collection_names: set[str] = set()
            for collection in collections:
                dirname = available_directory_name(
                    collection["name"], collection["id"], used_collection_names
                )
                self._export_collection(connection, collection["id"], collections_dir / dirname)

            children: dict[str | None, list[Bundle]] = {}
            for bundle in bundles.values():
                children.setdefault(bundle.parent_id, []).append(bundle)

            used_root_names: set[str] = set()
            for bundle in children.get(None, []):
                dirname = available_directory_name(bundle.name, bundle.id, used_root_names)
                self._export_bundle(connection, bundle, bundles_dir / dirname, children)

        action = "Would export" if self.dry_run else "Exported"
        print(
            f"{action} {self.files_exported} file(s) "
            f"({self.bytes_exported:,} bytes) to {self.output}"
        )

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        required = {"files", "collections", "collection_files", "bundles", "bundle_files"}
        actual = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = required - actual
        if missing:
            raise ExportError(f"database is missing table(s): {', '.join(sorted(missing))}")

    @staticmethod
    def _validate_bundle_tree(bundles: dict[str, Bundle]) -> None:
        for bundle in bundles.values():
            if bundle.parent_id is not None and bundle.parent_id not in bundles:
                raise ExportError(
                    f"bundle {bundle.id} refers to missing parent {bundle.parent_id}"
                )
            seen: set[str] = set()
            current: Bundle | None = bundle
            while current is not None:
                if current.id in seen:
                    raise ExportError(f"cycle in bundle hierarchy at {current.id}")
                seen.add(current.id)
                current = bundles.get(current.parent_id) if current.parent_id else None

    def _export_collection(
        self, connection: sqlite3.Connection, collection_id: str, destination: Path
    ) -> None:
        self._make_directory(destination)
        rows = connection.execute(
            """
            SELECT cf.file_sha256_hash AS hash, f.extension
            FROM collection_files AS cf
            JOIN files AS f ON f.sha256_hash = cf.file_sha256_hash
            WHERE cf.collection_id = ?
            ORDER BY cf.inserted_ts, cf.file_sha256_hash
            """,
            (collection_id,),
        )
        for row in rows:
            suffix = f".{row['extension']}" if row["extension"] else ""
            self._copy_stored_file(row["hash"], destination / f"{row['hash']}{suffix}")

    def _export_bundle(
        self,
        connection: sqlite3.Connection,
        bundle: Bundle,
        destination: Path,
        children: dict[str | None, list[Bundle]],
    ) -> None:
        self._make_directory(destination)
        used_names: set[str] = set()
        rows = connection.execute(
            """
            SELECT file_sha256_hash AS hash, file_name
            FROM bundle_files
            WHERE bundle_id = ?
            ORDER BY inserted_ts, file_sha256_hash
            """,
            (bundle.id,),
        )
        for row in rows:
            filename = safe_name(row["file_name"], "bundle file")
            if filename in used_names:
                raise ExportError(f"duplicate name in bundle {bundle.id}: {filename!r}")
            used_names.add(filename)
            self._copy_stored_file(row["hash"], destination / filename)

        for child in children.get(bundle.id, []):
            dirname = available_directory_name(child.name, child.id, used_names)
            self._export_bundle(connection, child, destination / dirname, children)

    def _make_directory(self, path: Path) -> None:
        if self.dry_run:
            return
        if path.exists() and not path.is_dir():
            raise ExportError(f"output path is not a directory: {path}")
        path.mkdir(parents=True, exist_ok=True)

    def _copy_stored_file(self, file_hash: str, destination: Path) -> None:
        source = self.storage / safe_name(file_hash, "file hash")
        if not source.is_file():
            raise ExportError(f"stored file not found: {source}")
        if destination.exists() and not self.overwrite:
            raise ExportError(
                f"output already exists: {destination} (use --overwrite to replace files)"
            )
        self.files_exported += 1
        self.bytes_exported += source.stat().st_size
        if not self.dry_run:
            shutil.copy2(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export all Filebase collections and bundle trees."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--storage", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace output files that already exist (unrelated files are retained)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and report without writing files"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        Exporter(
            args.database,
            args.storage,
            args.output,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        ).run()
    except (ExportError, sqlite3.Error, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
