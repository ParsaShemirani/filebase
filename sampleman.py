from models import File, Description, Edge
from connection import Session

file = File(
    inserted_ts="ZIMMY",
    name="Jameswebb",
    sha256_hash="DSLKFJSLDKJ2d34234LKJKLJ",
    extension="mp4",
    size=239489,
    created_ts="TODAY"
)

description = Description(
    inserted_ts="NOW",
    text="MONEYMAN"
)

edge = Edge(
    type="has_description",
    source_node=file,
    target_node=description,
    inserted_ts="MONEYDAY"
)

with Session() as session:
    with session.begin():
        session.add_all([file, description, edge])

