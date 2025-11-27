from models import FileRelationship
from connection import Session

with Session() as session:
    with session.begin():
        rel = FileRelationship(
            source_id=1096,
            target_id=299,
            kind="crop_of"
        )
        session.add(rel)