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

CREATE TABLE file_relationships (
    id INTEGER NOT NULL PRIMARY KEY,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES files(id),
    FOREIGN KEY (target_id) REFERENCES files(id)
);

CREATE TABLE labels (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    inserted_ts TEXT NOT NULL,
    description TEXT
);

CREATE TABLE file_labels (
    id INTEGER NOT NULL PRIMARY KEY,
    file_id INTEGER NOT NULL,
    label_id INTEGER NOT NULL,
    inserted_ts TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (label_id) REFERENCES labels(id)
);


PRAGMA foreign_keys = ON;