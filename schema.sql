PRAGMA foreign_keys = ON;

CREATE TABLE files (
    sha256_hash TEXT PRIMARY KEY,
    size_bytes INTEGER NOT NULL,
    extension TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    inserted_ts TEXT NOT NULL, 
    
    name TEXT,
    other_json TEXT
);


CREATE TABLE bundles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL
);

CREATE TABLE bundle_files (
    bundle_id TEXT NOT NULL,
    path TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (bundle_id, path),

    FOREIGN KEY (bundle_id) REFERENCES bundles(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
);

CREATE TABLE directories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    parent_id TEXT,

    FOREIGN KEY (parent_id) REFERENCES directories(id)
);

CREATE TABLE directory_files (
    directory_id TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (directory_id, file_sha256_hash),

    FOREIGN KEY (directory_id) REFERENCES directories(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
);

CREATE TABLE directory_bundles (
    directory_id TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (directory_id, bundle_id),

    FOREIGN KEY (directory_id) REFERENCES directories(id),
    FOREIGN KEY (bundle_id) REFERENCES bundles(id)
);