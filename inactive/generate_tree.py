"""
generate_tree.py - Updated version

Changes:
1. File counts inside parentheses now represent the TOTAL recursive file count.
2. Files directly inside a collection are shown as a child node:
       - X file(s) in this collection
3. Subcollections are still shown normally.
"""

from connection import Session
from models import Collection, File


def build_indexes(session):
    """Build lookup tables for:
    - child collections
    - files that belong directly to each collection
    """

    collections = session.query(Collection).all()
    files = session.query(File).all()

    children_map = {}
    direct_files_map = {}

    # Setup dictionary slots
    for c in collections:
        children_map.setdefault(c.parent_id, []).append(c)
        direct_files_map.setdefault(c.id, [])

    # Assign files to their direct parent collections
    for f in files:
        if f.collection_id is not None:
            direct_files_map.setdefault(f.collection_id, []).append(f)

    return children_map, direct_files_map


def compute_total_files(collection, children_map, direct_files_map, cache):
    """Compute recursive file count for a collection."""
    if collection.id in cache:
        return cache[collection.id]

    total = len(direct_files_map.get(collection.id, []))

    for child in children_map.get(collection.id, []):
        total += compute_total_files(child, children_map, direct_files_map, cache)

    cache[collection.id] = total
    return total


def render_tree(collection, children_map, direct_files_map, total_file_cache, indent=""):
    lines = []

    # Recursive file count
    total_files = total_file_cache[collection.id]

    # Header for this collection
    lines.append(f"{indent}- {collection.name}  (total: {total_files} files)")

    next_indent = indent + "    "

    # --- 1. Child collections ---
    child_collections = children_map.get(collection.id, [])
    for child in sorted(child_collections, key=lambda c: c.name.lower()):
        lines.extend(
            render_tree(child, children_map, direct_files_map, total_file_cache, next_indent)
        )

    # --- 2. Direct files in this collection ---
    direct_files = direct_files_map.get(collection.id, [])
    if direct_files:
        lines.append(f"{next_indent}- {len(direct_files)} file(s) in this collection")

    return lines


def generate_tree_output():
    session = Session()

    children_map, direct_files_map = build_indexes(session)

    # Identify top-level collections
    top_level = children_map.get(None, [])

    # Compute recursive file counts
    total_file_cache = {}
    for c in top_level:
        compute_total_files(c, children_map, direct_files_map, total_file_cache)

    output = ["COLLECTION TREE OVERVIEW\n"]

    if not top_level:
        output.append("(No collections found)")
    else:
        for c in sorted(top_level, key=lambda x: x.name.lower()):
            # Ensure recursive totals for all descendants are cached
            compute_total_files(c, children_map, direct_files_map, total_file_cache)
            output.extend(render_tree(c, children_map, direct_files_map, total_file_cache))

    session.close()
    return "\n".join(output)


def main():
    text = generate_tree_output()
    out_path = "collection_tree.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Tree written to {out_path}")


if __name__ == "__main__":
    main()
