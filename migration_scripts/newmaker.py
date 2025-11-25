import pandas as pd
from sqlalchemy import create_engine, text

# Load CSVs
collections = pd.read_csv("new_collections.csv")
files = pd.read_csv("new_files.csv")

# -----------------------------
# PROCESS COLLECTIONS
# -----------------------------

# Sort and reassign new IDs
collections = collections.sort_values("id").reset_index(drop=True)
collections["new_id"] = collections.index + 1

# Map old→new collection IDs
col_id_map = dict(zip(collections["id"], collections["new_id"]))

# Remap parent_id using new IDs
collections["parent_id"] = collections["parent_id"].map(col_id_map)

# Clean up fields
collections = (
    collections
    .drop(columns=["id"])
    .rename(columns={"new_id": "id"})
)

# Ensure correct column order
collections = collections[[
    "id",
    "name",
    "inserted_ts",
    "parent_id",
    "description"
]]

# Convert parent_id to nullable Int64 and None
collections["parent_id"] = (
    collections["parent_id"]
    .astype("Int64")
    .where(collections["parent_id"].notna(), None)
)

# -----------------------------
# PROCESS FILES
# -----------------------------

# Sort and assign new IDs
files = files.sort_values("id").reset_index(drop=True)
files["new_id"] = files.index + 1

# Map old file IDs → new ones (just for internal reference)
file_id_map = dict(zip(files["id"], files["new_id"]))

# Apply new file IDs
files = (
    files
    .drop(columns=["id"])
    .rename(columns={"new_id": "id"})
)

# Remap file → collection relationships
files["collection_id"] = files["collection_id"].map(col_id_map)

# Ensure correct column order
files = files[[
    "id",
    "name",
    "sha256_hash",
    "extension",
    "size",
    "created_ts",
    "inserted_ts",
    "collection_id",
    "description"
]]

files["collection_id"] = (
    files["collection_id"]
    .astype("Int64")
    .where(files["collection_id"].notna(), None)
)

# -----------------------------
# DATABASE SETUP
# -----------------------------

engine = create_engine("sqlite:///way2maniq.db")

schema_sql = """

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
"""

# Execute schema setup
with engine.begin() as conn:
    for stmt in schema_sql.split(";"):
        s = stmt.strip()
        if s:
            conn.execute(text(s))

# Insert data
collections.to_sql("collections", engine, if_exists="append", index=False)
files.to_sql("files", engine, if_exists="append", index=False)

print("Database created successfully.")
