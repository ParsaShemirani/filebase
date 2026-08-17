from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
from textual import log

from models import File, Directory, DirectoryFile, StorageDevice, StorageDeviceFile
from connection import Session


def get_parent_directory(directory: Directory) -> Directory | None:
    with Session() as session:
        return session.scalar(
            select(Directory).where(Directory.id == directory.parent_id)
        )


def get_child_directories(directory: Directory | None) -> list[Directory]:
    if directory is not None:
        directory_id = directory.id
    else:
        directory_id = None

    with Session() as session:
        return session.scalars(
            select(Directory).where(Directory.parent_id == directory_id)
        ).all()


def get_directory_files(directory: Directory) -> list[DirectoryFile]:
    with Session() as session:
        return session.scalars(
            select(DirectoryFile).where(DirectoryFile.directory_id == directory.id)
        ).all()


def generate_directory_path(directory: Directory | None) -> str:
    if directory is None:
        return "/"

    reverse_directory_list = [directory]

    with Session() as session:

        def append_parents(d: Directory):
            parent_directory = session.scalar(
                select(Directory).where(Directory.id == d.parent_id)
            )
            if parent_directory is not None:
                reverse_directory_list.append(parent_directory)
                append_parents(parent_directory)
            else:
                return

        append_parents(directory)

    directory_list = reversed(reverse_directory_list)
    return "/" + "/".join(directory.name for directory in directory_list)


### WRITERS


def rename_directory(directory: Directory, new_name: str) -> None:
    with Session() as session:
        with session.begin():
            directory.name = new_name
            session.add(directory)


def rename_directory_file(directory_file: DirectoryFile, new_name: str) -> None:
    with Session() as session:
        with session.begin():
            directory_file.file_name = new_name
            session.add(directory_file)


def move_directory(
    directory: Directory, new_parent_directory: Directory | None
) -> None:
    with Session() as session:
        with session.begin():
            if new_parent_directory is not None:
                directory.parent_id = new_parent_directory.id
            else:
                directory.parent_id = None
            session.add(directory)


def move_directory_file(
    directory_file: DirectoryFile, new_directory: Directory
) -> None:
    with Session() as session:
        with session.begin():
            directory_file.directory_id = new_directory.id
            session.add(directory_file)


def make_directory(name: str, parent_id: str | None) -> None:
    with Session() as session:
        with session.begin():
            directory = create_directory(name, parent_id)
            session.add(directory)

def cut_paste_directories(directory_ids: set[str], destination_directory: Directory) -> None:
    with Session() as session:
        with session.begin():
            for d_id in directory_ids:
                directory = session.scalar(select(Directory).where(Directory.id == d_id))
                
