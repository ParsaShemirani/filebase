"""
Abstract

Start with a list of file extensions that proxies will be generated for.
Ex: {"jpg", "mp4", "mp3", "png", "raw"}

Then, scan from file number one and up. First check:
Is this file a proxy itself? (Instant disqualifier)
If not, does this file already have a proxy? (Instant disqualifer)

If qualified, start the type-specific process to generate the proxy file
based on the original.

The name of the new file will be the id of the original, followed by {proxy}.ext

Once the file is created, create the file entry as usual and add it. Then create a new FileRelationship
and add that as well. After both suceed, copy2 the file to the storage and the tempdir block terminates.

"""

import tempfile
import subprocess
import shutil
from pathlib import Path

from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session as SessionType


from env_vars import STORAGE_PATH
from ingest import create_file
from models import File, FileRelationship
from connection import Session

image_extensions = {"arw", "dng", "jpg", "png", "tif", "tiff", "heic"}
audio_extensions = {"wav", "aiff", "aif", "flac", "mp3", "aac", "m4a", "ogg", "opus"}
video_extensions = {"mp4", "mov", "m4v", "avi", "mkv", "webm", "mpeg", "mpg"}

all_proxy_extensions = image_extensions | audio_extensions | video_extensions


def make_image_proxy(input_file_path: Path, output_file_path: Path):
    cmd = [
        "sips",
        str(input_file_path),
        "--resampleWidth",
        "1000",
        "--setProperty",
        "format",
        "jpeg",
        "--setProperty",
        "formatOptions",
        "32",
        "--out",
        str(output_file_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_video_proxy(input_file_path: Path, output_file_path: Path):
    cmd = [
        "ffmpeg",
        "-threads",
        "2",
        "-i",
        str(input_file_path),
        "-vf",
        "scale=1000:-2",
        "-c:v",
        "libx264",
        "-crf",
        "32",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        str(output_file_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def make_audio_proxy(input_file_path: Path, output_file_path: Path):
    cmd = [
        "ffmpeg",
        "-threads",
        "2",
        "-i",
        str(input_file_path),
        "-ac",
        "1",  # mono
        "-q:a",
        "7",  # VBR quality level
        str(output_file_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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



with Session() as session:
    all_files = session.scalars(select(File)).all()

for f in all_files:
    with Session() as session:
        with session.begin():
            existing_proxy = get_proxy_of(f.id, session)
            existing_master = get_master_of(f.id, session)
            if existing_proxy is not None or existing_master is not None:
                continue

            if f.extension not in all_proxy_extensions:
                continue

            master_file_path = STORAGE_PATH / f"{f.id}.{f.extension}"
            if not master_file_path.is_file():
                continue

            
            print(f"Generating proxy for file id: {f.id}")
            with tempfile.TemporaryDirectory() as tempdir:
                tempdir_path = Path(tempdir)
                proxy_path = None

                if f.extension in image_extensions:
                    proxy_path = tempdir_path / f"proxy.jpg"
                    make_image_proxy(input_file_path=master_file_path, output_file_path=proxy_path)
                elif f.extension in video_extensions:
                    proxy_path = tempdir_path / f"proxy.mp4"
                    make_video_proxy(input_file_path=master_file_path, output_file_path=proxy_path)
                elif f.extension in audio_extensions:
                    proxy_path = tempdir_path / f"proxy.mp3"
                    make_audio_proxy(input_file_path=master_file_path, output_file_path=proxy_path)

                if proxy_path is None:
                    raise ValueError("Houston, we have a problem.")
                

                proxy_file = create_file(proxy_path)
                session.add(proxy_file)
                session.flush()
                print("Inserted Proxy File:")
                print(proxy_file)

                proxy_relationship = FileRelationship(
                    source_id=proxy_file.id,
                    target_id=f.id,
                    kind="proxy_of"
                )
                session.add(proxy_relationship)
                session.flush()
                print("Inserted Proxy Relationship:")
                print(proxy_relationship)

                shutil.copy2(str(proxy_path), str(STORAGE_PATH / f"{proxy_file.id}.{proxy_file.extension}"))





