from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from hashlib import file_digest
from pathlib import Path

from db_funcs import DatabaseService
from env_vars import OUTGOING_PATH_STR, STORAGE_PATH_STR
from models import Directory, DirectoryFile, File


IGNORED_NAMES = {".DS_Store"}
OUTGOING_PATH = Path(OUTGOING_PATH_STR)
STORAGE_PATH = Path(STORAGE_PATH_STR)


def require_existing_directory(path: Path) -> None:
    if not path.is_dir():
        raise NotADirectoryError(f"{path} is not an existing directory")


def should_ignore_path(path: Path) -> bool:
    return path.name in IGNORED_NAMES


def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def get_stats_json(file_path: Path) -> str:
    stats = file_path.stat()
    stats_dict = {
        name: getattr(stats, name)
        for name in dir(stats)
        if name.startswith("st_")
    }
    return json.dumps(stats_dict, indent=None)


def build_directory(name: str, parent_id: str | None) -> Directory:
    return Directory(
        id=str(uuid.uuid4()),
        name=name,
        parent_id=parent_id,
    )


def build_file(file_path: Path) -> File:
    return File(
        sha256_hash=generate_sha256_hash(file_path),
        size_bytes=file_path.stat().st_size,
    )


def build_directory_file(
    directory: Directory,
    file: File,
    file_path: Path,
) -> DirectoryFile:
    return DirectoryFile(
        id=str(uuid.uuid4()),
        directory_id=directory.id,
        file_sha256_hash=file.sha256_hash,
        file_name=file_path.name,
        stats_json=get_stats_json(file_path),
    )


@dataclass
class DirectoryNode:
    db: DatabaseService
    directory: Directory
    files: list[File] = field(default_factory=list)
    directory_files: list[DirectoryFile] = field(default_factory=list)
    children: list[DirectoryNode] = field(default_factory=list)
    source_file_paths: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        directory_path: Path,
        db: DatabaseService,
        parent_id: str | None = None,
    ) -> DirectoryNode:
        directory = build_directory(directory_path.name, parent_id)
        directory_node = cls(db, directory)

        for child_path in directory_path.iterdir():
            if should_ignore_path(child_path):
                continue

            if child_path.is_file():
                file = build_file(child_path)
                directory_file = build_directory_file(directory, file, child_path)

                directory_node.files.append(file)
                directory_node.directory_files.append(directory_file)
                directory_node.source_file_paths.setdefault(
                    file.sha256_hash,
                    child_path,
                )

            elif child_path.is_dir():
                child_directory_node = cls.from_path(child_path, db, directory.id)
                directory_node.children.append(child_directory_node)

        return directory_node

    @classmethod
    def from_db(
        cls,
        directory_id: str,
        db: DatabaseService,
    ) -> DirectoryNode:
        directory = db.get_directory_from_id(directory_id)
        directory_node = cls(db, directory)
        directory_node.directory_files = db.get_directory_files(directory.id)
        directory_node.files = [
            db.get_file_from_sha256_hash(directory_file.file_sha256_hash)
            for directory_file in directory_node.directory_files
        ]

        for child_directory in db.get_child_directories(directory.id):
            child_directory_node = cls.from_db(child_directory.id, db)
            directory_node.children.append(child_directory_node)

        return directory_node

    def get_all_directories(self) -> list[Directory]:
        directories = [self.directory]

        for child in self.children:
            directories.extend(child.get_all_directories())

        return directories

    def get_all_files(self) -> list[File]:
        files = list(self.files)

        for child in self.children:
            files.extend(child.get_all_files())

        return files

    def get_all_unique_files(self) -> list[File]:
        seen_file_hashes: set[str] = set()
        unique_files: list[File] = []

        for file in self.get_all_files():
            if file.sha256_hash not in seen_file_hashes:
                seen_file_hashes.add(file.sha256_hash)
                unique_files.append(file)

        return unique_files

    def get_all_directory_files(self) -> list[DirectoryFile]:
        directory_files = list(self.directory_files)

        for child in self.children:
            directory_files.extend(child.get_all_directory_files())

        return directory_files

    def get_import_objects(self) -> list[object]:
        return [
            *self.get_all_directories(),
            *self.get_all_unique_files(),
            *self.get_all_directory_files(),
        ]

    def get_source_file_path_map(self) -> dict[str, Path]:
        source_file_paths = dict(self.source_file_paths)

        for child in self.children:
            for file_hash, file_path in child.get_source_file_path_map().items():
                source_file_paths.setdefault(file_hash, file_path)

        return source_file_paths

    def get_directory_path_map(self, root_path: Path) -> dict[str, Path]:
        current_path = root_path / self.directory.name
        directory_path_map = {self.directory.id: current_path}

        for child in self.children:
            directory_path_map.update(child.get_directory_path_map(current_path))

        return directory_path_map

    def get_directory_file_path_map(self, root_path: Path) -> dict[str, Path]:
        current_path = root_path / self.directory.name
        directory_file_path_map: dict[str, Path] = {}

        for directory_file in self.directory_files:
            directory_file_path_map[directory_file.id] = (
                current_path / directory_file.file_name
            )

        for child in self.children:
            directory_file_path_map.update(
                child.get_directory_file_path_map(current_path)
            )

        return directory_file_path_map

    def stage_files_to_outgoing(self) -> None:
        require_existing_directory(OUTGOING_PATH)

        for file_hash, source_path in self.get_source_file_path_map().items():
            destination_path = OUTGOING_PATH / file_hash
            if destination_path.exists():
                continue

            shutil.copy2(source_path, destination_path)

    def resolve_storage_file_path(self, file_hash: str) -> Path:
        require_existing_directory(STORAGE_PATH)
        storage_file_path = STORAGE_PATH / file_hash

        if not storage_file_path.is_file():
            raise FileNotFoundError(f"{file_hash} not found at {storage_file_path}")

        return storage_file_path

    def retrieve_to_path(self, output_root: Path) -> None:
        require_existing_directory(output_root)
        current_path = output_root / self.directory.name
        current_path.mkdir()

        for directory_file in self.directory_files:
            source_path = self.resolve_storage_file_path(
                directory_file.file_sha256_hash
            )
            destination_path = current_path / directory_file.file_name
            shutil.copy2(source_path, destination_path)

        for child in self.children:
            child.retrieve_to_path(current_path)

    def insert_to_db(self) -> None:
        self.db.insert_objects(self.get_import_objects())
