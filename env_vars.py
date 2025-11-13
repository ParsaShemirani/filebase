import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATABASE_PATH = Path(os.getenv("DATABASE_PATH"))

STORAGE_PATH = Path(os.getenv("STORAGE_PATH"))

TERMINAL_PATH = Path(os.getenv("TERMINAL_PATH"))

