CREATE TABLE collections (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    parent_id INTEGER,
    description TEXT,
    FOREIGN KEY (parent_id) REFERENCES collections(id)
);
CREATE TABLE files (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    sha256_hash TEXT NOT NULL UNIQUE,
    extension TEXT NOT NULL,
    size INTEGER NOT NULL,
    created_ts TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    collection_id INTEGER,
    description TEXT,
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);


PRAGMA foreign_keys = ON;