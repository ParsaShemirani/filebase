import pandas as pd
from pathlib import Path

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

# CSVs containing the *old* IDs (same ones used previously)
COLLECTIONS_CSV = "new_collections.csv"
FILES_CSV = "new_files.csv"

# Directory containing the actual files that still use old IDs
STORAGE_DIR = Path("/Users/parsahome/main/filebase/storage")

# Optional: set to True to only print what would happen
DRY_RUN = False

# A unique marker to avoid colliding with real filenames
TMP_MARKER = "__reindex_tmp__"


# -------------------------------------------------
# LOAD CSVs
# -------------------------------------------------

collections = pd.read_csv(COLLECTIONS_CSV)
files = pd.read_csv(FILES_CSV)

# -------------------------------------------------
# REBUILD COLLECTION ID MAP (same as original script)
# -------------------------------------------------

collections = collections.sort_values("id").reset_index(drop=True)
collections["new_id"] = collections.index + 1
col_id_map = dict(zip(collections["id"], collections["new_id"]))

# -------------------------------------------------
# REBUILD FILE ID MAP (same as original script)
# -------------------------------------------------

files = files.sort_values("id").reset_index(drop=True)
files["new_id"] = files.index + 1

file_id_map = dict(zip(files["id"], files["new_id"]))

print(f"Loaded {len(file_id_map)} file ID mappings.")

# -------------------------------------------------
# BUILD RENAME PLAN
# -------------------------------------------------

rename_plan = []  # list of (orig_path, tmp_path, final_path)

for path in STORAGE_DIR.iterdir():
    if not path.is_file():
        continue

    stem = path.stem  # e.g. "153" from "153.arw"
    suffix = path.suffix  # e.g. ".arw"

    # Only handle files whose stem is an integer
    try:
        old_id = int(stem)
    except ValueError:
        # Not an ID-based filename; skip
        continue

    if old_id not in file_id_map:
        print(f"⚠️  No mapping for old_id {old_id} (file: {path.name})")
        continue

    new_id = file_id_map[old_id]

    # If the ID doesn't change, we don't need to rename this file
    if new_id == old_id:
        continue

    # Temporary unique name: "<old_id>__reindex_tmp__<new_id><ext>"
    tmp_name = f"{old_id}{TMP_MARKER}{new_id}{suffix}"
    tmp_path = STORAGE_DIR / tmp_name

    # Final desired name: "<new_id><ext>"
    final_name = f"{new_id}{suffix}"
    final_path = STORAGE_DIR / final_name

    # Sanity check: temp name shouldn't already exist
    if tmp_path.exists():
        raise RuntimeError(
            f"Temporary file already exists: {tmp_path}. "
            f"Aborting to avoid data loss."
        )

    rename_plan.append((path, tmp_path, final_path))

print(f"Planned {len(rename_plan)} renames (where old_id != new_id).")

if not rename_plan:
    print("Nothing to do.")
    exit(0)

# -------------------------------------------------
# FIRST PASS: rename originals → temporary names
# -------------------------------------------------

print("\n=== First pass: renaming to temporary names ===")
for orig_path, tmp_path, final_path in rename_plan:
    print(f"{orig_path.name}  →  {tmp_path.name}")
    if not DRY_RUN:
        orig_path.rename(tmp_path)

# -------------------------------------------------
# SECOND PASS: rename temporary names → final names
# -------------------------------------------------

print("\n=== Second pass: renaming temporary → final names ===")
for orig_path, tmp_path, final_path in rename_plan:
    # At this point, tmp_path should exist if not DRY_RUN
    # Final path should *not* exist yet in a consistent mapping.
    print(f"{tmp_path.name}  →  {final_path.name}")

    if not DRY_RUN:
        if final_path.exists():
            raise RuntimeError(
                f"Final target already exists unexpectedly: {final_path}. "
                f"Aborting to avoid overwriting."
            )
        tmp_path.rename(final_path)

print("\nDone.")
