from langchain_openai import OpenAIEmbeddings

from settings import OPENAI_API_KEY

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def generate_embedding(text: str) -> list[float]:
    embedding = embeddings.embed_query(text=text)
    return embedding