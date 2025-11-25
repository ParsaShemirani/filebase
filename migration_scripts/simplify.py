from old_models import File, Collection, ISO_FMT_Z, Edge, Description
from sqlalchemy import select
from connection import engine
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from audio_recording import interactive_transcribe
from pathlib import Path
import pandas as pd

simp_output_dir = Path(__file__).parent / "simp_csv"
simp_output_dir.mkdir(exist_ok=True)

collections_query = """
SELECT
  collections.id,
  collections.name,
  nodes.inserted_ts,
  descriptions.text AS description
FROM collections
JOIN nodes
  ON nodes.id = collections.id
LEFT JOIN edges
  ON edges.source_id = collections.id
  AND edges.type = 'has_description'
LEFT JOIN descriptions
  ON descriptions.id = edges.target_id;
"""

files_query = """
SELECT
  files.id,
  files.name,
  files.sha256_hash,
  files.extension,
  files.size,
  files.created_ts,
  nodes.inserted_ts,
  coll_edges.target_id AS collection_id,
  descriptions.text AS description
FROM files
JOIN nodes
  ON nodes.id = files.id
LEFT JOIN edges AS coll_edges
  ON files.id = coll_edges.source_id
  AND coll_edges.type = 'in_collection'
LEFT JOIN edges AS desc_edges
  ON files.id = desc_edges.source_id
  AND desc_edges.type = 'has_description'
LEFT JOIN descriptions
  ON descriptions.id = desc_edges.target_id;
"""

with engine.connect() as con:
    collections_df = pd.read_sql(collections_query, con)
    collections_file = simp_output_dir / "collections.csv"
    collections_df.to_csv(collections_file, index=False)

    files_df = pd.read_sql(files_query, con)
    files_df['collection_id'] = files_df['collection_id'].astype('Int64')
    files_file = simp_output_dir / "files.csv"
    files_df.to_csv(files_file, index=False)