import json
import shutil
from pathlib import Path
from dataclasses import dataclass

from env_vars import PENDING_STORAGE_JSON, STORAGE_PATH_STR


@dataclass
class PendingStorage:
    id: str
    path: str


def load_pending_items() -> list[PendingStorage]:
    try:
        with open(PENDING_STORAGE_JSON, "r", encoding="utf-8") as data_file:
            items_dict: dict[str, str] = json.load(data_file)
            return [PendingStorage(id=k, path=v) for k, v in items_dict.items()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_pending_items(pending_items: list[PendingStorage]) -> None:
    items_dict = {item.id: item.path for item in pending_items}
    with open(PENDING_STORAGE_JSON, "w", encoding="utf-8") as data_file:
        json.dump(items_dict, data_file, indent=4)


def add_pending_items(new_pending_items: list[PendingStorage]) -> None:
    pending_items = load_pending_items()
    pending_items.extend(new_pending_items)
    save_pending_items(pending_items)


def delete_pending_items(old_pending_items: list[PendingStorage]) -> None:
    pending_items = load_pending_items()
    ids_to_remove = {item.id for item in old_pending_items}
    updated_pending_items = [item for item in pending_items if item.id not in ids_to_remove]
    save_pending_items(updated_pending_items)


def to_store_size() -> int:
    pending_items = load_pending_items()

    total_bytes = 0
    for item in pending_items:
        file_path = Path(item.path)
        total_bytes += file_path.stat().st_size

    return total_bytes

def store_pending_items() -> None:
    pending_items = load_pending_items()

    for item in pending_items:
        file_path = Path(item.path)
        storage_file_path = Path(STORAGE_PATH_STR) / item.id

        print(f"Storing {file_path}")
        shutil.copy(file_path, storage_file_path)

    delete_pending_items(pending_items)