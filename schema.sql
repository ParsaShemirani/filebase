PRAGMA foreign_keys = ON;

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    sha256_hash TEXT NOT NULL UNIQUE,
    extension TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    created_ts TEXT
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
    file_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (bundle_id, file_id),

    FOREIGN KEY (bundle_id) REFERENCES bundles(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);