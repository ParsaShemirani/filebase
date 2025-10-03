from pathlib import Path
from datetime import datetime
import os

def date_edit():
    target_dir = Path("/Users/parsahome/archive_program/staging/timez")
    epoch_time = datetime(2010, 6, 20).timestamp()

    # recurse through files
    for file_path in target_dir.rglob("*"):
        if file_path.is_file():
            os.utime(file_path, (epoch_time, epoch_time))
            print(f"Updated: {file_path}")


def remove_file_kind():
    target_dir = Path("/Users/parsahome/archive_program/staging")
    target_extension = ".moi"

    for item in target_dir.iterdir():
        if item.is_file() and item.suffix.lower() == target_extension:
            item.unlink()




def mod_to_mpg():
    target_dir = Path("/Users/parsahome/archive_program/staging")
    
    for item in target_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".mod":
            new_path = item.with_suffix(".mpg")
            item.rename(new_path)
            print(f"Renamed: {item.name} -> {new_path.name}")