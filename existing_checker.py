from sqlalchemy import select

from models import File
from connection import Session
from settings import staging_directory
from ingest import generate_sha256_hash

file_list = [
    f
    for f in staging_directory.iterdir()
    if f.is_file() and not f.name.startswith(".")
]

for f in file_list:
    sha256_hash = generate_sha256_hash(f)
    with Session() as session:
        existing_file = session.scalar(
            select(File).where(File.sha256_hash == sha256_hash)
        )
        if existing_file:
            print(f"Existing file found. Path: {str(f)}. ID: {existing_file.id}. Collection id: {existing_file.collection_id}")
        else:
            print(f"No duplicate for {str(f)}")
