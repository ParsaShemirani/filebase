import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select, or_
from sqlalchemy.orm import Session as SessionType

from env_vars import STORAGE_PATH, TERMINAL_PATH
from models import File, FileRelationship
from ingest import create_file

image_exts = {"arw", "dng", "jpg", "png", "tif", "tiff", "heic"}
audio_exts = {"wav", "aiff", "aif", "flac", "mp3", "aac", "m4a", "ogg", "opus"}
video_exts = {"mp4", "mov", "m4v", "avi", "mkv", "webm", "mpeg", "mpg"}


@dataclass
class DerivationConfig:
    kind: str
    output_extension: str
    qualifies: Callable[[File, SessionType], bool]
    generate: Callable[[Path, Path], None]


def derivation_exists(file: File, kind: str, session: SessionType) -> bool:
    existing_relationship = session.scalar(
        select(FileRelationship).where(
            or_(
                FileRelationship.source_id == file.id,
                FileRelationship.target_id == file.id,
            ),
            FileRelationship.kind == kind,
        )
    )

    return existing_relationship is not None


def run_derivation(file: File, session: SessionType, cfg: DerivationConfig) -> None:
    if derivation_exists(file, cfg.kind, session):
        return None
    if not cfg.qualifies(file, session):
        return None

    input_path = STORAGE_PATH / f"{file.id}.{file.extension}"
    temp_output_path = TERMINAL_PATH / f"{cfg.kind}.{cfg.output_extension}"

    cfg.generate(input_path, temp_output_path)

    derived_file = create_file(temp_output_path)
    session.add(derived_file)
    session.flush()

    session.add(
        FileRelationship(source_id=file.id, target_id=derived_file.id, kind=cfg.kind)
    )
    session.flush()

    final_path = STORAGE_PATH / f"{derived_file.id}.{derived_file.extension}"
    shutil.copy2(str(temp_output_path), str(final_path))
    temp_output_path.unlink()


# Derivation Implementations


## image_proxy
def image_proxy_qualifies(file: File, session: SessionType) -> bool:
    return file.extension in image_exts


def image_proxy_generate(input_path: Path, output_path: Path) -> None:
    cmd = [
        "sips",
        str(input_path),
        "--resampleWidth",
        "1000",
        "--setProperty",
        "format",
        "jpeg",
        "--setProperty",
        "formatOptions",
        "32",
        "--out",
        str(output_path),
    ]

    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


image_proxy_config = DerivationConfig(
    kind="image_proxy",
    output_extension="jpg",
    qualifies=image_proxy_qualifies,
    generate=image_proxy_generate,
)


## video_proxy
def video_proxy_qualifies(file: File, session: SessionType) -> bool:
    return file.extension in video_exts


def video_proxy_generate(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-threads",
        "2",
        "-i",
        str(input_path),
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
        str(output_path),
    ]

    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


video_proxy_config = DerivationConfig(
    kind="video_proxy",
    output_extension="mp4",
    qualifies=video_proxy_qualifies,
    generate=video_proxy_generate,
)


# audio_proxy
def audio_proxy_qualifies(file: File, session: SessionType) -> bool:
    return file.extension in audio_exts


def audio_proxy_generate(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-threads",
        "2",
        "-i",
        str(input_path),
        "-ac",
        "1",  # mono
        "-q:a",
        "7",  # VBR quality level
        str(output_path),
    ]

    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


audio_proxy_config = DerivationConfig(
    kind="audio_proxy",
    output_extension="mp3",
    qualifies=audio_proxy_qualifies,
    generate=audio_proxy_generate,
)
