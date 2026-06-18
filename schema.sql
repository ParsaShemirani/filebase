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
    parent_id TEXT,
    inserted_ts TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES bundles(id)
);

CREATE TABLE file_bundles (
    file_id TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (file_id, bundle_id),

    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (bundle_id) REFERENCES bundles(id)
);