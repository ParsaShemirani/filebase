import os
from dotenv import load_dotenv

load_dotenv()

def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"{name} not set in .env")
    return value

DATABASE_PATH: str = get_required_env("DATABASE_PATH")