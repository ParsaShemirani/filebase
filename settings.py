from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

json_database_directory = Path("/Users/parsahome/json_filebase")
staging_directory = Path("/Users/parsahome/json_filebase/staging")
intake_storage_device_id = 1
