from pathlib import Path
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
import shutil
from pprint import pprint

from tabulate import tabulate
import typer
from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Bundle, BundleFile
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
        created_ts=get_file_modified_time_str(file_path=file_path)
    )

def create_bundle(bundle_path: Path, parent_id: str | None) -> Bundle:
    return Bundle(
        id=str(uuid.uuid4()),
        name=bundle_path.name,
        inserted_ts=get_current_time_str(),
        parent_id=parent_id,
    )

def create_bundle_file(bundle: Bundle, file: File, file_path: Path) -> BundleFile:
    return BundleFile(
        bundle_id=bundle.id,
        file_id=file.id,
        file_name=file_path.name,
        inserted_ts=get_current_time_str(),
    )

def build_bundle(bundle_path: Path, parent_id: str | None):
    files: list[File] = []
    bundles: list[Bundle] = []
    bundle_files: list[BundleFile] = []
    file_path_dict: dict[str, Path] = {}

    bundle = create_bundle(bundle_path=bundle_path, parent_id=parent_id)
    bundles.append(bundle)

    for child_path in bundle_path.iterdir():
        if should_ignore_path(path=child_path):
            continue

        if child_path.is_file():
            file = create_file(file_path=child_path)
            bundle_file = create_bundle_file(bundle=bundle, file=file, file_path=child_path)
            files.append(file)
            bundle_files.append(bundle_file)
            file_path_dict[file.id] = child_path

        elif child_path.is_dir():
            child_files, child_bundles, child_bundle_files, child_file_path_dict = build_bundle(bundle_path=child_path, parent_id = bundle.id)
            files.extend(child_files)
            bundles.extend(child_bundles)
            bundle_files.extend(child_bundle_files)
            file_path_dict.update(child_file_path_dict)
    return files, bundles, bundle_files, file_path_dict


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

def load_bundle(bundle_id: str, session: SessionType):
    files: list[File] = []
    bundles: list[Bundle] = []
    bundle_files: list[BundleFile] = []


    bundle = session.scalar(select(Bundle).where(Bundle.id == bundle_id))
    if bundle is None:
        raise ValueError("Bundle not found")
    child_bundles = session.scalars(
        select(Bundle).where(Bundle.parent_id == bundle_id)
    ).all()
    child_files = session.scalars(
        select(File)
        .join(BundleFile, File.id == BundleFile.file_id)
        .where(BundleFile.bundle_id == bundle_id)
    ).all()

    child_bundle_files = session.scalars(
        select(BundleFile).where(BundleFile.bundle_id == bundle_id)
    ).all()

    bundles.append(bundle)
    files.extend(child_files)
    bundle_files.extend(child_bundle_files)

    for child_bundle in child_bundles:
        nested_files, nested_bundles, nested_bundle_files = load_bundle(bundle_id=child_bundle.id, session=session)
        files.extend(nested_files)
        bundles.extend(nested_bundles)
        bundle_files.extend(nested_bundle_files)
        
    return files, bundles, bundle_files


def retrieve_bundle(bundle_id: str, parent_dir: Path, session: SessionType) -> None:
    bundle = session.scalar(select(Bundle).where(Bundle.id == bundle_id))
    if bundle is None:
        raise ValueError("Bundle not found")
    output_dir = parent_dir / bundle.name
    output_dir.mkdir()
    bundle_files = session.scalars(select(BundleFile).where(BundleFile.bundle_id == bundle_id)).all()
    for bundle_file in bundle_files:
        storage_file_path = STORAGE_PATH / bundle_file.file_id
        destination_file_path = output_dir / bundle_file.file_name
        shutil.copy(src=str(storage_file_path), dst=str(destination_file_path))
    child_bundles = session.scalars(
        select(Bundle).where(Bundle.parent_id == bundle_id)
    ).all()

    for child_bundle in child_bundles:
        retrieve_bundle(bundle_id=child_bundle.id, parent_dir=output_dir, session=session)


def main(insert_bundle: str = None, load_bundle_id: str = None, retrieve_bundle_id: str = None):
    if insert_bundle:
        files, bundles, bundle_files, file_path_dict = build_bundle(
            bundle_path=Path(insert_bundle),
            parent_id=None
        )
        file_ids = [f.id for f in files]

        tabulate_objects(objects=files, max_width=20)
        tabulate_objects(objects=bundles, max_width=20)
        tabulate_objects(objects=bundle_files, max_width=20)

        if input("Copy to terminal? (y/n): ").lower() == "y":
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
                    session.add_all(bundle_files)
            print("All objects added to database!")


    if load_bundle_id:
        with Session() as session:
            files, bundles, bundle_files = load_bundle(bundle_id=load_bundle_id, session=session)
            pprint(files)
            pprint(bundles)
            pprint(bundle_files)

    if retrieve_bundle_id:
        with Session() as session:
            retrieve_bundle(bundle_id=retrieve_bundle_id, parent_dir=TERMINAL_PATH, session=session)

        

if __name__ == "__main__":
    typer.run(main)