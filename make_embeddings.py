from pathlib import Path

from sqlalchemy import select
from openai import OpenAI
from tabulate import tabulate

from settings import OPENAI_API_KEY
from connection import Session
from models import File, Collection
from vector_math import cosine_similarity
from audio_recording import interactive_transcribe

col_emb_path = Path("/Users/parsahome/main/inbox/col_emb")

file_emb_path = Path("/Users/parsahome/main/inbox/file_emb")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_sorted_files(dir_path: Path) -> list[Path] | None:
    file_paths = sorted(
        [f for f in dir_path.glob("*") if not f.name.startswith(".") and f.is_file()]
    )
    if file_paths:
        return file_paths
    else:
        return None
    
def generate_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def generate_collection_embeddings():
    col_embs = get_sorted_files(col_emb_path)

    if col_embs:
        existers = {int(ce.stem) for ce in col_embs}
    else:
        existers = {}

    with Session() as session:
        all_collections = session.scalars(
            select(Collection)
        ).all()

        for c in all_collections:
            if not c.id in existers:
                embedding = generate_embedding(c.description)
                
                csv_embedding = ",".join([str(x) for x in embedding])

                output_file_path = col_emb_path / f"{c.id}.csv"
                output_file_path.write_text(csv_embedding)
                print(f"Completed: ID {c.id}")

def generate_file_embeddings():
    file_emb_paths = get_sorted_files(file_emb_path)

    if file_emb_paths:
        existers = {int(fe.stem) for fe in file_emb_paths}
    else:
        existers = {}

    with Session() as session:
        all_files = session.scalars(
            select(File)
        ).all()

        for f in all_files:
            if not f.id in existers:
                if f.description is not None:
                    embedding = generate_embedding(f.description)
                    csv_embedding = ",".join([str(x) for x in embedding])

                    output_file_path = file_emb_path / f"{f.id}.csv"
                    output_file_path.write_text(csv_embedding)
                    print(f"Completed: ID {f.id}")



def see_relevant_collections():
    print("Transcribe the search text. ")

    search_text = interactive_transcribe()

    print("Converting to embedding.")
    search_embedding = generate_embedding(search_text)
    print("Done")

    col_emb_paths = get_sorted_files(col_emb_path)

    similarities = []
    
    print("Reading and calculating.")

    for cep in col_emb_paths:
        with Session() as session:
            c_obj = session.scalar(select(Collection).where(Collection.id == int(cep.stem)))
        
        c_emb = [float(x) for x in cep.read_text().split(",")]
        similarities.append((int(cep.stem), cosine_similarity(search_embedding, c_emb), c_obj.description))

    sorted_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:3]

    print(tabulate(sorted_similarities, headers=["ID", "Similarity Score", "Description"], tablefmt="grid", maxcolwidths=30))


def see_relevant_files():
    print("Transcribe the search text. ")

    search_text = interactive_transcribe()

    print("Converting to embedding.")
    search_embedding = generate_embedding(search_text)
    print("Done")

    file_emb_paths = get_sorted_files(file_emb_path)

    similarities = []
    
    print("Reading and calculating.")

    for f in file_emb_paths:
        with Session() as session:
            f_obj = session.scalar(select(File).where(File.id == int(f.stem)))
        
        f_emb = [float(x) for x in f.read_text().split(",")]
        similarities.append((int(f.stem), cosine_similarity(search_embedding, f_emb), f_obj.description))

    sorted_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:3]

    print(tabulate(sorted_similarities, headers=["ID", "Similarity Score", "Description"], tablefmt="grid", maxcolwidths=30))



if __name__ == "__main__":
    see_relevant_collections()
    #see_relevant_files()
    #generate_file_embeddings()