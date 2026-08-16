import os
from dotenv import load_dotenv

load_dotenv()

def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"{name} not set in .env")
    return value

DATABASE_PATH_STR = get_required_env("DATABASE_PATH_STR")
PENDING_STORAGE_PATH = get_required_env("PENDING_STORAGE_PATH")
STORAGE_PATH_STR = get_required_env("STORAGE_PATH_STR")