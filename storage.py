from __future__ import annotations
from functools import wraps
from pathlib import Path

from db_funcs import DatabaseService
from models import File, Directory, DirectoryFile, StorageDevice, StorageDeviceFile
from env_vars import DATABASE_PATH_STR

db = DatabaseService()


class StorageService:
    def store_file(self, file_sha256_hash: str, storage_device_id: str) -> None:
        db.get_file_from_sha256_hash(file_sha256_hash)
        db.get_storage_device_from_id(storage_device_id)
        
        storage_device_file = StorageDeviceFile(storage_device_id, file_sha256_hash)


