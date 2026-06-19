import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
import typer
from tabulate import tabulate

from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Bundle, BundleFile
from connection import Session



IGNORED_NAMES = {".DS_Store"}

TERMINAL_PATH = Path(TERMINAL_PATH_STR)
STORAGE_PATH = Path(STORAGE_PATH_STR)

def should_ignore_path(path: Path) -> bool:
    return path.name in IGNORED_NAMES

def get_fs_created_time(file_path: Path) -> datetime:
    modified_ts = file_path.stat().st_mtime
    return datetime.fromtimestamp(modified_ts, tz=timezone.utc)

def generate_sha256_hash(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()
    
def create_file(file_path: Path) -> File:
    return File(
        sha256_hash=generate_sha256_hash(file_path=file_path),
        extension=file_path.suffix.lstrip(".").lower(),
        fs_created_ts=get_fs_created_time(file_path=file_path).isoformat(),
        inserted_ts=datetime.now(timezone.utc).isoformat()
    )

def create_bundle(directory_path: Path, parent_id: str | None) -> Bundle:
    return Bundle(
        id=str(uuid.uuid4()),
        name=directory_path.name,
        inserted_ts=datetime.now(timezone.utc).isoformat(),
        parent_id=parent_id,
    )

def create_bundle_file(bundle: Bundle, file: File, file_path: Path) -> BundleFile:
    return BundleFile(
        bundle_id=bundle.id,
        file_sha256_hash=file.sha256_hash,
        file_name=file_path.name,
        inserted_ts=datetime.now(timezone.utc).isoformat(),
    )

def build_bundle(directory_path: Path, parent_id: str | None) -> tuple[list[File], list[Bundle], list[BundleFile], dict[str, Path]]:
    files: list[File] = []
    bundles: list[Bundle] = []
    bundle_files: list[BundleFile] = []
    file_path_dict: dict[str, Path] = {}

    bundle = create_bundle(directory_path=directory_path, parent_id=parent_id)
    bundles.append(bundle)

    for child_path in directory_path.iterdir():
        if should_ignore_path(path=child_path):
            continue

        if child_path.is_file():
            child_file = create_file(file_path=child_path)
            child_bundle_file = create_bundle_file(bundle=bundle, file=child_file, file_path=child_path)
            files.append(child_file)
            bundle_files.append(child_bundle_file)
            file_path_dict[child_file.sha256_hash] = child_path
        
        elif child_path.is_dir():
            nested_files, nested_bundles, nested_bundle_files, nested_file_path_dict = build_bundle(directory_path=child_path, parent_id=bundle.id)
            files.extend(nested_files)
            bundles.extend(nested_bundles)
            bundle_files.extend(nested_bundle_files)
            file_path_dict.update(nested_file_path_dict)
    
    return files, bundles, bundle_files, file_path_dict

def retrieve_bundle(bundle_id: str, parent_dir: Path, session: SessionType) -> None:
    bundle = session.scalar(select(Bundle).where(Bundle.id == bundle_id))
    if bundle is None:
        raise ValueError(f"Bundle id {bundle_id} not found")
    
    output_dir = parent_dir / bundle.name
    output_dir.mkdir()

    bundle_files = session.scalars(select(BundleFile).where(BundleFile.bundle_id == bundle_id)).all()

    for bundle_file in bundle_files:
        storage_file_path = STORAGE_PATH / bundle_file.file_sha256_hash
        destination_file_path = output_dir / bundle_file.file_name
        shutil.copy(src=str(storage_file_path), dst=str(destination_file_path))
    
    child_bundles = session.scalars(select(Bundle).where(Bundle.parent_id == bundle_id)).all()
    for child_bundle in child_bundles:
        retrieve_bundle(bundle_id=child_bundle.id, parent_dir=output_dir, session=Session)



## TYPER CLI

def tabulate_objects(objects: list[object], max_width: int) -> None:
    if not objects:
        print("Empty")
        return

    print(tabulate([asdict(object) for object in objects], headers="keys", tablefmt="grid", maxcolwidths=max_width))

app = typer.Typer()

@app.command()
def xinsert_bundle(directory_path_str: str):
    files, bundles, bundle_files, file_path_dict = build_bundle(directory_path=Path(directory_path_str), parent_id=None)

    tabulate_objects(objects=files, max_width=20)
    tabulate_objects(objects=bundles, max_width=20)
    tabulate_objects(objects=bundle_files, max_width=20)

    if input("Copy to terminal? (y/n): ") == "y":
        db_inserted_path = TERMINAL_PATH / "db_inserted"
        db_inserted_path.mkdir()
        for file in files:
            shutil.copy(src=str(file_path_dict[file.sha256_hash]), dst=str(db_inserted_path / file.sha256_hash))
        print(f"All files copied to {str(db_inserted_path)}")

    print(f"Database path: {DATABASE_PATH_STR}")
    if input("Insert into database? (y/n): ") == "y":
        with Session() as session:
            with session.begin():
                session.add_all(files)
                session.add_all(bundles)
                session.add_all(bundle_files)
        print("All objects added to database")


@app.command()
def xretrieve_bundle(bundle_id: str):
    with Session() as session:
        retrieve_bundle(bundle_id=bundle_id, parent_dir=TERMINAL_PATH, session=session)

if __name__ == "__main__":
    app()