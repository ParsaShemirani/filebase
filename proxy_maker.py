import tempfile
import subprocess
import shutil
from pathlib import Path

from sqlalchemy import select, or_


from env_vars import STORAGE_PATH
from ingest import create_file
from models import File, FileRelationship
from connection import Session

with Session() as session:
    with session.begin():
        all_jpegs = session.scalars(
            select(File).where(or_(File.extension == "jpg", File.extension == "jpeg"))
        )
        for j in all_jpegs:
            disqualifier = session.scalar(
                select(FileRelationship).where(or_(FileRelationship.source_id == j.id, FileRelationship.target_id == j.id), FileRelationship.kind == "proxy_of")
            )
            if disqualifier:
                continue

            original_path = STORAGE_PATH / f"{j.id}.{j.extension}"
            
            with tempfile.TemporaryDirectory() as tmpdir:
                proxy_temp_path = Path(tmpdir) / "proxy.jpg"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", str(original_path),
                    "-q:v", "5",
                    str(proxy_temp_path)
                ]

                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("GENERATED")

                proxy_file = create_file(proxy_temp_path)
                session.add(proxy_file)
                session.flush()
                print(proxy_file)

                proxy_relationship = FileRelationship(source_id=proxy_file.id, target_id=j.id, kind="proxy_of")
                session.add(proxy_relationship)
                session.flush()
                print(proxy_relationship)

                shutil.copy2(str(proxy_temp_path), str(STORAGE_PATH / f"{proxy_file.id}.jpg"))



