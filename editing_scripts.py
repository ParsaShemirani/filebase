from pathlib import Path
from datetime import datetime
import os

def date_edit():
    target_dir = Path("/Users/parsahome/archive_program/staging/")
    epoch_time = datetime(2016, 1, 1).timestamp()

    # recurse through files
    for file_path in target_dir.rglob("*"):
        if file_path.is_file():
            os.utime(file_path, (epoch_time, epoch_time))
            print(f"Updated: {file_path}")

def file_date_edit():
    target_file = Path("/Users/parsahome/archive_program/staging/MOV00A.mp4")
    epoch_time = datetime(2016, 1, 1).timestamp()
    os.utime(target_file, (epoch_time, epoch_time))
    print(f"Updated: {target_file}")

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


if __name__ == "__main__":
    if input("Date edit? :") == "y":
        date_edit()
    elif input("File date edit?") == "y":
        file_date_edit()
    elif input("RFK?: ") == "y":
        remove_file_kind()
    elif input("Mod to mpg?: ") == "y":
        mod_to_mpg()