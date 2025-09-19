from os import getenv
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

filebase_path = getenv("filebase_path")

active_directory = Path("/Users/parsashemirani/Main/fakeactive")

intake_storage_device_path = Path("/Users/parsashemirani/Main/fakeintake")


OPENAI_API_KEY = getenv("OPENAI_API_KEY")