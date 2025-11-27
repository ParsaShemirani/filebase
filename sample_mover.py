import shutil


from sqlalchemy import select

from ingest import get_sorted_files
from models import File, Collection, FileRelationship

from env_vars import STORAGE_PATH, TERMINAL_PATH

from connection import Session


with Session() as session:
    wanted_files = session.scalars(
        select(File).where(File.collection_id == 26, File.extension == "jpg")
    ).all()


    money_dir = TERMINAL_PATH / "money"

    for wf in wanted_files:
        print(wf.id)
        proxy_file = session.scalar(select(File).join(FileRelationship, File.id == FileRelationship.source_id).where(FileRelationship.target_id == wf.id, FileRelationship.kind == "proxy_of"))
        
        shutil.copy2(str(STORAGE_PATH / f"{proxy_file.id}.jpg"), str(money_dir))