CREATE TABLE files (
    sha256_hash TEXT PRIMARY KEY,
    size_bytes INTEGER NOT NULL,
    extension TEXT NOT NULL,
    created_ts TEXT NOT NULL,
    inserted_ts TEXT NOT NULL, 

    other_json TEXT
);

CREATE TABLE storage_devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL
);

CREATE TABLE storage_files (
    storage_device_id TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,

    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (storage_device_id, file_sha256_hash),

    FOREIGN KEY (storage_device_id) REFERENCES storage_devices(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
);

CREATE TABLE storage_file_events (
    id TEXT PRIMARY KEY,
    storage_device_id TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,

    event_type TEXT NOT NULL,
    event_ts TEXT NOT NULL,

    FOREIGN KEY (storage_device_id) REFERENCES storage_devices(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
);

CREATE TABLE file_instance (
    file_sha256_hash TEXT PRIMARY KEY,

    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    description TEXT
);

CREATE TABLE bundles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    description TEXT
);

CREATE TABLE bundle_files (
    bundle_id TEXT NOT NULL,
    path TEXT NOT NULL,
    file_sha256_hash TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,

    PRIMARY KEY (bundle_id, path),

    FOREIGN KEY (bundle_id) REFERENCES bundles(id),
    FOREIGN KEY (file_sha256_hash) REFERENCES files(sha256_hash)
)
