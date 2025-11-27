from pathlib import Path

from sqlalchemy import select
from openai import OpenAI
from tabulate import tabulate

from env_vars import OPENAI_API_KEY, EMBEDDINGS_PATH
from connection import Session
from models import File, Collection
from vector_math import cosine_similarity
from audio_recording import interactive_transcribe

client = OpenAI(api_key=OPENAI_API_KEY)

def get_sorted_files(dir_path: Path) -> list[Path] | None:
    file_paths = sorted(
        [f for f in dir_path.glob("*") if not f.name.startswith(".") and f.is_file()]
    )
    if file_paths:
        return file_paths
    else:
        return None
    
def get_embedding_paths(file_only: bool = False, collection_only: bool = False) -> list[Path] | None:
    sorted_embedding_paths = get_sorted_files(EMBEDDINGS_PATH)
    if sorted_embedding_paths:
        if file_only:
            file_embedding_paths = [ef for ef in sorted_embedding_paths if ef.name.startswith('f')]
            return file_embedding_paths
        elif collection_only:
            collection_embedding_paths = [ef for ef in sorted_embedding_paths if ef.name.startswith('c')]
            return collection_embedding_paths
        else:
            return sorted_embedding_paths


def generate_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def generate_collection_embeddings():
    collection_embedding_paths = get_embedding_paths(collection_only=True)

    if collection_embedding_paths:
        existers = {int(ef.stem[1:]) for ef in collection_embedding_paths}
    else:
        existers = {}

    with Session() as session:
        all_collections = session.scalars(
            select(Collection)
        ).all()

        for c in all_collections:
            if not c.id in existers:
                if c.description is not None:
                    embedding = generate_embedding(c.description)
                    
                    csv_embedding = ",".join([str(x) for x in embedding])

                    output_file_path = EMBEDDINGS_PATH / f"c{c.id}.csv"
                    output_file_path.write_text(csv_embedding)
                    print(f"Completed Collection: ID {c.id}")

def generate_file_embeddings():
    file_embedding_paths = get_embedding_paths(file_only=True)

    if file_embedding_paths:
        existers = {int(ef.stem[1:]) for ef in file_embedding_paths}
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

                    output_file_path = EMBEDDINGS_PATH / f"f{f.id}.csv"
                    output_file_path.write_text(csv_embedding)
                    print(f"Completed File: ID {f.id}")

def searcher() -> None:
    print("Transcribe the search text. ")
    search_text = interactive_transcribe()
    search_embedding = generate_embedding(search_text)

    embedding_paths = get_embedding_paths()
    similarities = []
    with Session() as session:
        for ep in embedding_paths:
            embedding = [float(x) for x in ep.read_text().split(",")]
            if ep.stem.startswith('f'):
                file = session.scalar(select(File).where(File.id == int(ep.stem[1:])))
                similarities.append(
                    (
                        "file",
                        file.id,
                        cosine_similarity(search_embedding, embedding),
                        file.description
                    )
                )
            elif ep.stem.startswith('c'):
                collection = session.scalar(select(Collection).where(Collection.id == int(ep.stem[1:])))
                similarities.append(
                    (
                        "collection",
                        collection.id,
                        cosine_similarity(search_embedding, embedding),
                        collection.description
                    )
                )
            else:
                raise ValueError("Houston, we have a problem.")
            
    
    sorted_similarities = sorted(similarities, key=lambda x: x[2], reverse=True)[:3]
    print(tabulate(sorted_similarities, headers=["Type", "ID", "Similarity Score", "Description"], tablefmt="grid", maxcolwidths=30))




if __name__ == "__main__":
    searcher()