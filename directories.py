import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from hashlib import file_digest
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType
import typer
from tabulate import tabulate

from env_vars import DATABASE_PATH_STR, TERMINAL_PATH_STR, STORAGE_PATH_STR
from models import File, Bundle, BundleFile, Directory, DirectoryFile, DirectoryBundle
from connection import Session


def create_directory(session: SessionType, name: str, parent_id: str | None) -> Directory:
    session.add