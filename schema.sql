CREATE TABLE files (
    id TEXT PRIMARY KEY,
    sha256_hash NOT NULL,
    size_bytes NOT NULL,
    extension NOT NULL,
    inserted_at NOT NULL,


    fs_created_at TEXT,
    fs_modified_at TEXT
)