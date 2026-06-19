from pathlib import Path
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
import shutil

from tabulate import tabulate
import typer
from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR
from models import File, Bundle, FileBundle
from connection import Session
from hashlib import file_digest


IGNORED_NAMES = {".DS_Store"}

TERMINAL_PATH = Path(TERMINAL_PATH_STR)

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

    files: list[File] = []
    bundles: list[Bundle] = [bundle]
    file_bundles: list[FileBundle] = []
    file_path_dict: dict[str, Path] = {}

    for child_path in bundle_path.iterdir():
        if should_ignore_path(path=child_path):
            continue

        if child_path.is_file():
            file = create_file(file_path=child_path)
            file_bundle = create_file_bundle(file=file, bundle=bundle, file_path=child_path)
            files.append(file)
            file_bundles.append(file_bundle)
            file_path_dict[file.id] = child_path

        elif child_path.is_dir():
            child_files, child_bundles, child_file_bundles, child_file_path_dict = build_bundle(bundle_path=child_path, parent_id = bundle.id)
            files.extend(child_files)
            bundles.extend(child_bundles)
            file_bundles.extend(child_file_bundles)
            file_path_dict.update(child_file_path_dict)
    return files, bundles, file_bundles, file_path_dict


def tabulate_objects(objects: list[object], max_width: int) -> None:
    if not objects:
        print("Empty")
        return

    print(
        tabulate(
            [asdict(obj) for obj in objects],
            headers="keys",
            tablefmt="grid",
            maxcolwidths=max_width
        )
    )

def main(bundle_str: str = None):
    if bundle_str:
        files, bundles, file_bundles, file_path_dict = build_bundle(
            bundle_path=Path(bundle_str),
            parent_id=None
        )
        file_ids = [f.id for f in files]

        tabulate_objects(objects=files, max_width=20)
        tabulate_objects(objects=bundles, max_width=20)
        tabulate_objects(objects=file_bundles, max_width=20)

        if input("Copy to terminal? (y/n)").lower() == "y":
            db_inserted_folder_path = TERMINAL_PATH / "db_inserted"
            db_inserted_folder_path.mkdir(exist_ok=False)
            for file_id in file_ids:
                shutil.copy(
                    src=str(file_path_dict[file_id]),
                    dst=str(db_inserted_folder_path / file_id),
                )

        print(f"Database Path: {DATABASE_PATH_STR}")
        if input("Insert into database? (y/n): ").lower() == "y":
            with Session() as session:
                with session.begin():
                    session.add_all(files)
                    session.add_all(bundles)
                    session.add_all(file_bundles)
            print("All objects added to database!")


        

if __name__ == "__main__":
    typer.run(main)