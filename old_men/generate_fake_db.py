from __future__ import annotations

import argparse
import hashlib
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import factory
import factory.random
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from old_men.models import Base, Directory, DirectoryFile, File


DEFAULT_OUTPUT_PATH = Path("fake_filebase.db")
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

ADJECTIVES = [
    "amber",
    "brave",
    "bright",
    "calm",
    "clever",
    "cosmic",
    "crimson",
    "curious",
    "electric",
    "golden",
    "hidden",
    "lunar",
    "patient",
    "quiet",
    "rapid",
    "silver",
    "steady",
    "velvet",
]
NOUNS = [
    "atlas",
    "bridge",
    "camera",
    "garden",
    "harbor",
    "journal",
    "lantern",
    "memo",
    "notebook",
    "passport",
    "recipe",
    "signal",
    "sketch",
    "station",
    "ticket",
    "voyage",
]
EXTENSIONS = ["jpg", "pdf", "txt", "md", "png", "mp3", "csv", "zip"]


fake = Faker()


class DirectoryFactory(factory.Factory):
    class Meta:
        model = Directory

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.LazyFunction(lambda: fake.unique.slug())
    inserted_ts = factory.Sequence(lambda index: iso_time(index))
    parent_id = None


class FileFactory(factory.Factory):
    class Meta:
        model = File

    sha256_hash = factory.Sequence(
        lambda index: hashlib.sha256(f"fake-file-{index}".encode()).hexdigest()
    )
    size_bytes = factory.Sequence(lambda index: 1024 + ((index * 7919) % 8_000_000))
    inserted_ts = factory.Sequence(lambda index: iso_time(index))


class DirectoryFileFactory(factory.Factory):
    class Meta:
        model = DirectoryFile

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    directory_id = ""
    file_name = factory.LazyFunction(lambda: f"{fake.slug()}.txt")
    file_sha256_hash = ""
    stats_json = "{}"
    inserted_ts = factory.Sequence(lambda index: iso_time(index))


def main() -> None:
    args = parse_args()
    output_path = args.output.expanduser()
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"{output_path} already exists. Pass --overwrite to replace it.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    directories, files, directory_files = build_fake_data(
        seed=args.seed,
        directory_count=args.directories,
        file_count=args.files,
        max_files_per_directory=args.max_files_per_directory,
    )
    create_database(temp_path, directories, files, directory_files)
    temp_path.replace(output_path)

    print(f"Wrote {output_path}")
    print(f"directories: {len(directories)}")
    print(f"files: {len(files)}")
    print(f"directory_files: {len(directory_files)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a fake filebase database.")
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--directories", type=int, default=18)
    parser.add_argument("--files", type=int, default=60)
    parser.add_argument("--max-files-per-directory", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def build_fake_data(
    seed: int,
    directory_count: int,
    file_count: int,
    max_files_per_directory: int,
) -> tuple[list[Directory], list[File], list[DirectoryFile]]:
    if directory_count < 1:
        raise SystemExit("--directories must be at least 1.")
    if file_count < 0:
        raise SystemExit("--files cannot be negative.")
    if max_files_per_directory < 1:
        raise SystemExit("--max-files-per-directory must be at least 1.")

    rng = random.Random(seed)
    Faker.seed(seed)
    factory.random.reseed_random(seed)
    fake.unique.clear()

    directories = make_directories(rng, directory_count)
    files = FileFactory.build_batch(file_count)
    directory_files = make_directory_files(
        rng=rng,
        directories=directories,
        files=files,
        max_files_per_directory=max_files_per_directory,
    )
    return directories, files, directory_files


def make_directories(rng: random.Random, count: int) -> list[Directory]:
    directories: list[Directory] = []
    sibling_names: dict[str | None, set[str]] = {None: set()}

    for _ in range(count):
        parent_id = None
        if directories and rng.random() > 0.35:
            parent_id = rng.choice(directories).id
        name = unique_name(sibling_names.setdefault(parent_id, set()), handle(rng))
        directory = DirectoryFactory(name=name, parent_id=parent_id)
        directories.append(directory)
        sibling_names.setdefault(directory.id, set())

    return directories


def make_directory_files(
    rng: random.Random,
    directories: list[Directory],
    files: list[File],
    max_files_per_directory: int,
) -> list[DirectoryFile]:
    directory_files: list[DirectoryFile] = []
    names_by_directory: dict[str, set[str]] = {directory.id: set() for directory in directories}

    for file in files:
        directory = choose_directory_with_space(rng, directories, directory_files, max_files_per_directory)
        if directory is None:
            break

        file_name = unique_name(
            names_by_directory[directory.id],
            f"{handle(rng)}.{rng.choice(EXTENSIONS)}",
        )
        directory_files.append(
            DirectoryFileFactory(
                directory_id=directory.id,
                file_name=file_name,
                file_sha256_hash=file.sha256_hash,
                stats_json=json.dumps(fake_stats(file.size_bytes), sort_keys=True),
            )
        )

    return directory_files


def choose_directory_with_space(
    rng: random.Random,
    directories: list[Directory],
    directory_files: list[DirectoryFile],
    max_files_per_directory: int,
) -> Directory | None:
    counts = {directory.id: 0 for directory in directories}
    for directory_file in directory_files:
        counts[directory_file.directory_id] += 1
    available = [
        directory
        for directory in directories
        if counts[directory.id] < max_files_per_directory
    ]
    return rng.choice(available) if available else None


def unique_name(used_names: set[str], name: str) -> str:
    if name not in used_names:
        used_names.add(name)
        return name

    suffix = 2
    stem, dot, extension = name.rpartition(".")
    while True:
        candidate = (
            f"{stem}-{suffix}.{extension}" if dot else f"{name}-{suffix}"
        )
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        suffix += 1


def handle(rng: random.Random) -> str:
    return f"{rng.choice(ADJECTIVES)}-{rng.choice(NOUNS)}"


def fake_stats(size_bytes: int) -> dict[str, int]:
    return {
        "st_mode": 33188,
        "st_nlink": 1,
        "st_size": size_bytes,
    }


def create_database(
    database_path: Path,
    directories: list[Directory],
    files: list[File],
    directory_files: list[DirectoryFile],
) -> None:
    engine = create_engine("sqlite:///" + str(database_path), echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        with session.begin():
            session.add_all(files)
            session.add_all(directories)
            session.add_all(directory_files)
    engine.dispose()


def iso_time(offset: int) -> str:
    return (BASE_TIME + timedelta(minutes=offset)).isoformat()


if __name__ == "__main__":
    main()
