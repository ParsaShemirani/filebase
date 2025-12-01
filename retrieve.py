import tempfile
import subprocess
import shutil
from pathlib import Path
from typing_extensions import Annotated

from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session as SessionType
import typer


from env_vars import STORAGE_PATH, TERMINAL_PATH
from ingest import create_file
from models import File, FileRelationship, Label, FileLabel
from connection import Session

image_extensions = {"arw", "dng", "jpg", "png", "tif", "tiff", "heic"}
audio_extensions = {"wav", "aiff", "aif", "flac", "mp3", "aac", "m4a", "ogg", "opus"}
video_extensions = {"mp4", "mov", "m4v", "avi", "mkv", "webm", "mpeg", "mpg"}

all_proxy_extensions = image_extensions | audio_extensions | video_extensions


def get_proxy_of(file_id: int, session: SessionType) -> File | None:
    return session.scalar(
        select(File).join(
            FileRelationship,
            and_(
                FileRelationship.source_id == File.id,
                FileRelationship.kind == "proxy_of",
                FileRelationship.target_id == file_id,
            ),
        )
    )


def get_master_of(file_id: int, session: SessionType) -> File | None:
    return session.scalar(
        select(File).join(
            FileRelationship,
            and_(
                FileRelationship.target_id == File.id,
                FileRelationship.kind == "proxy_of",
                FileRelationship.source_id == file_id,
            ),
        )
    )


def main(
    file_id: Annotated[int, typer.Option("--file_id", "-fid")] = None,
    collection_id: Annotated[int, typer.Option("--collection_id", "-cid")] = None,
    label_id: Annotated[int, typer.Option("--label_id", "-lid")] = None,
    proxy: Annotated[bool, typer.Option("--proxy", "-p")] = False,
):
    file_stmt = None

    if file_id:
        file_stmt = select(File).where(File.id == file_id)
    elif collection_id:
        file_stmt = select(File).where(File.collection_id == collection_id)
    elif label_id is not None:
        file_stmt = (
            select(File)
            .join(FileLabel, File.id == FileLabel.file_id)
            .join(Label, FileLabel.label_id == Label.id)
            .where(Label.id == label_id)
        )
    else:
        raise ValueError("Must input either file id, collection id, or label id")


    with Session() as session:
        master_files = session.scalars(file_stmt).all()

        for mf in master_files:
            proxy_file = get_proxy_of(mf.id, session)
            if proxy and proxy_file is not None:
                print(f"Copying proxy id {proxy_file.id} to terminal\n")
                shutil.copy2(str(STORAGE_PATH / f"{proxy_file.id}.{proxy_file.extension}"), str(TERMINAL_PATH))
            else:
                print(f"Copying master file id {mf.id} to terminal\n")
                shutil.copy2(str(STORAGE_PATH / f"{mf.id}.{mf.extension}"), str(TERMINAL_PATH))
            
if __name__ == "__main__":
    typer.run(main)