PRAGMA foreign_keys = ON;

CREATE TABLE files (
    sha256_hash TEXT PRIMARY KEY,
    extension TEXT NOT NULL,
    fs_created_ts TEXT NOT NULL,
    inserted_ts TEXT NOT NULL
);

CREATE TABLE bundles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    parent_id TEXT,
    FOREIGN KEY (parent_id) REFERENCES bundles(id)
);

CREATE TABLE bundle_files (
    bundle_id TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,
    file_name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (bundle_id, file_sha256_hash),

    FOREIGN KEY (bundle_id) REFERENCES bundles(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
);