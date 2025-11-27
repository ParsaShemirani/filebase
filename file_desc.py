from sqlalchemy import select

from models import File
from connection import Session
from audio_recording import interactive_transcribe

file_id = input("Enter file id")

with Session() as session:
    with session.begin():
        file = session.scalar(
            select(File).where(File.id == file_id)
        )
        print(file)

        file.description = interactive_transcribe()
        
        session.flush()
        print(file)
