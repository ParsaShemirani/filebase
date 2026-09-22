from pathlib import Path

from sqlalchemy import select

from db_funcs import Session
from env_vars import STORAGE_PATH_STR
from models import File


storage_path = Path(STORAGE_PATH_STR)

with Session() as session:
    for file_hash in session.scalars(select(File.sha256_hash)):
        if not (storage_path / file_hash).is_file():
            print(file_hash)
