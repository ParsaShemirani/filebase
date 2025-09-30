import json
from pathlib import Path
from hashlib import file_digest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pprint import pprint
import subprocess
import argparse
import shutil

from settings import database_path
from audio_recording import interactive_transcribe
from models import File, Collection


def create_file(file_path: Path) -> File:
