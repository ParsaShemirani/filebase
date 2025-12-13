import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

STR_DATA_DIRECTORY = os.getenv("DATA_DIRECTORY_PATH")
if not STR_DATA_DIRECTORY:
    raise RuntimeError("DATA_DIRECTORY_PATH not set in .env")

DATA_DIRECTORY_PATH = Path(STR_DATA_DIRECTORY)
DATABASE_PATH = DATA_DIRECTORY_PATH / "filebase.db"
STORAGE_PATH = DATA_DIRECTORY_PATH / "storage"
TERMINAL_PATH = DATA_DIRECTORY_PATH / "terminal"
EMBEDDINGS_PATH = DATA_DIRECTORY_PATH / "embeddings"


if __name__ == "__main__":
    for path in (DATA_DIRECTORY_PATH, STORAGE_PATH, TERMINAL_PATH, EMBEDDINGS_PATH):
        path.mkdir(parents=True, exist_ok=True) 
