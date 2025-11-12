import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATABASE_PATH = Path(os.getenv("DATABASE_PATH"))