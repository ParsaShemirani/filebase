from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#Include leading slash for absolute path
database_path = "/Users/parsahome/file_archive.db"

storage_directory = "/Users/parsahome/archive_storage"
