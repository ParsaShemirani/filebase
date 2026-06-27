from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from connection import Session
from env_vars import STORAGE_PATH_STR
from main import build_bundle, create_file
from models import Bundle, BundleFile, Directory, DirectoryBundle, DirectoryFile, File


ROOT_ID = "root"
HOST = "127.0.0.1"
PORT = 8080


def utc_now_str() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def normalize_directory_id(value: str | None) -> str | None:
    if value in (None, "", ROOT_ID):
        return None
    return value


def display_file_name(file: File) -> str:
    if file.name:
        return file.name
    short_hash = file.sha256_hash[:12]
    return f"{short_hash}.{file.extension}" if file.extension else short_hash


def item_payload(kind: str, id_: str, name: str, inserted_ts: str, **extra) -> dict:
    return {
        "kind": kind,
        "id": id_,
        "name": name,
        "inserted_ts": inserted_ts,
        **extra,
    }


def directory_to_tree(session, directory: Directory) -> dict:
    children = session.scalars(
        select(Directory)
        .where(Directory.parent_id == directory.id)
        .order_by(Directory.name, Directory.inserted_ts)
    ).all()
    return {
        "id": directory.id,
        "name": directory.name,
        "inserted_ts": directory.inserted_ts,
        "parent_id": directory.parent_id or ROOT_ID,
        "children": [directory_to_tree(session, child) for child in children],
    }


def is_descendant(session, directory_id: str, possible_parent_id: str) -> bool:
    current_id: str | None = directory_id
    while current_id:
        if current_id == possible_parent_id:
            return True
        directory = session.get(Directory, current_id)
        current_id = directory.parent_id if directory else None
    return False


def delete_directory_tree(session, directory_id: str) -> None:
    children = session.scalars(
        select(Directory.id).where(Directory.parent_id == directory_id)
    ).all()
    for child_id in children:
        delete_directory_tree(session, child_id)

    session.query(DirectoryFile).filter(
        DirectoryFile.directory_id == directory_id
    ).delete()
    session.query(DirectoryBundle).filter(
        DirectoryBundle.directory_id == directory_id
    ).delete()
    directory = session.get(Directory, directory_id)
    if directory:
        session.delete(directory)


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length == 0:
        return {}
    raw = handler.rfile.read(content_length)
    return json.loads(raw.decode("utf-8"))


def copy_to_storage_if_possible(source_path: Path, sha256_hash: str) -> None:
    storage_path = Path(STORAGE_PATH_STR)
    storage_path.mkdir(parents=True, exist_ok=True)
    destination = storage_path / sha256_hash
    if not destination.exists():
        shutil.copy2(source_path, destination)


class FilebaseWebHandler(BaseHTTPRequestHandler):
    server_version = "FilebaseWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_html(INDEX_HTML)
            return

        if parsed.path == "/api/tree":
            self.send_json(self.get_tree())
            return

        if parsed.path == "/api/contents":
            query = parse_qs(parsed.query)
            directory_id = normalize_directory_id(query.get("directory_id", [ROOT_ID])[0])
            self.send_json(self.get_contents(directory_id))
            return

        if parsed.path == "/api/detail":
            query = parse_qs(parsed.query)
            kind = query.get("kind", [""])[0]
            object_id = query.get("id", [""])[0]
            self.send_json(self.get_detail(kind, object_id))
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        try:
            body = parse_json_body(self)

            if parsed.path == "/api/directories":
                self.send_json(self.create_directory(body), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/files/attach":
                self.send_json(self.attach_file(body), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/files/import":
                self.send_json(self.import_file(body), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/bundles/attach":
                self.send_json(self.attach_bundle(body), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/bundles/import":
                self.send_json(self.import_bundle(body), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/move":
                self.send_json(self.move_object(body))
                return

            if parsed.path == "/api/remove":
                self.send_json(self.remove_object(body))
                return

            self.send_error_json(HTTPStatus.NOT_FOUND, "Not found")
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except IntegrityError:
            self.send_error_json(
                HTTPStatus.CONFLICT,
                "That object is already linked there, or the database rejected the change.",
            )
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")

        try:
            if len(parts) == 3 and parts[:2] == ["api", "directories"]:
                directory_id = parts[2]
                self.send_json(self.delete_directory(directory_id))
                return

            self.send_error_json(HTTPStatus.NOT_FOUND, "Not found")
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def get_tree(self) -> dict:
        with Session() as session:
            roots = session.scalars(
                select(Directory)
                .where(Directory.parent_id.is_(None))
                .order_by(Directory.name, Directory.inserted_ts)
            ).all()
            return {
                "id": ROOT_ID,
                "name": "Root",
                "children": [directory_to_tree(session, root) for root in roots],
            }

    def get_contents(self, directory_id: str | None) -> dict:
        with Session() as session:
            directory_name = "Root"
            if directory_id is not None:
                directory = session.get(Directory, directory_id)
                if not directory:
                    raise ValueError("Directory not found.")
                directory_name = directory.name

            child_filter = (
                Directory.parent_id.is_(None)
                if directory_id is None
                else Directory.parent_id == directory_id
            )
            directories = session.scalars(
                select(Directory)
                .where(child_filter)
                .order_by(Directory.name, Directory.inserted_ts)
            ).all()

            items = [
                item_payload(
                    "directory",
                    directory.id,
                    directory.name,
                    directory.inserted_ts,
                    parent_id=directory.parent_id or ROOT_ID,
                )
                for directory in directories
            ]

            if directory_id is not None:
                file_rows = (
                    session.query(DirectoryFile, File)
                    .join(File, DirectoryFile.file_sha256_hash == File.sha256_hash)
                    .filter(DirectoryFile.directory_id == directory_id)
                    .order_by(File.name, File.extension, File.sha256_hash)
                    .all()
                )
                for directory_file, file in file_rows:
                    items.append(
                        item_payload(
                            "file",
                            file.sha256_hash,
                            display_file_name(file),
                            directory_file.inserted_ts,
                            extension=file.extension,
                            sha256_hash=file.sha256_hash,
                        )
                    )

                bundle_rows = (
                    session.query(DirectoryBundle, Bundle)
                    .join(Bundle, DirectoryBundle.bundle_id == Bundle.id)
                    .filter(DirectoryBundle.directory_id == directory_id)
                    .order_by(Bundle.name, Bundle.inserted_ts)
                    .all()
                )
                for directory_bundle, bundle in bundle_rows:
                    items.append(
                        item_payload(
                            "bundle",
                            bundle.id,
                            bundle.name,
                            directory_bundle.inserted_ts,
                        )
                    )

            return {
                "directory_id": directory_id or ROOT_ID,
                "directory_name": directory_name,
                "items": items,
            }

    def get_detail(self, kind: str, object_id: str) -> dict:
        if not object_id:
            raise ValueError("Missing object id.")

        with Session() as session:
            if kind == "directory":
                directory = session.get(Directory, object_id)
                if not directory:
                    raise ValueError("Directory not found.")
                return {
                    "kind": "directory",
                    "id": directory.id,
                    "name": directory.name,
                    "parent_id": directory.parent_id or ROOT_ID,
                    "inserted_ts": directory.inserted_ts,
                    "child_directories": session.query(Directory)
                    .filter(Directory.parent_id == object_id)
                    .count(),
                    "files": session.query(DirectoryFile)
                    .filter(DirectoryFile.directory_id == object_id)
                    .count(),
                    "bundles": session.query(DirectoryBundle)
                    .filter(DirectoryBundle.directory_id == object_id)
                    .count(),
                }

            if kind == "file":
                file = session.get(File, object_id)
                if not file:
                    raise ValueError("File not found.")
                try:
                    stats = json.loads(file.stats_json)
                except json.JSONDecodeError:
                    stats = file.stats_json
                return {
                    "kind": "file",
                    "sha256_hash": file.sha256_hash,
                    "name": file.name,
                    "extension": file.extension,
                    "inserted_ts": file.inserted_ts,
                    "stats": stats,
                }

            if kind == "bundle":
                bundle = session.get(Bundle, object_id)
                if not bundle:
                    raise ValueError("Bundle not found.")
                bundle_files = session.scalars(
                    select(BundleFile)
                    .where(BundleFile.bundle_id == object_id)
                    .order_by(BundleFile.path)
                ).all()
                return {
                    "kind": "bundle",
                    "id": bundle.id,
                    "name": bundle.name,
                    "inserted_ts": bundle.inserted_ts,
                    "file_count": len(bundle_files),
                    "files": [
                        {"path": row.path, "sha256_hash": row.file_sha256_hash}
                        for row in bundle_files
                    ],
                }

        raise ValueError("Unknown object kind.")

    def create_directory(self, body: dict) -> dict:
        name = str(body.get("name", "")).strip()
        parent_id = normalize_directory_id(body.get("parent_id"))
        if not name:
            raise ValueError("Directory name is required.")

        with Session() as session:
            if parent_id is not None and not session.get(Directory, parent_id):
                raise ValueError("Parent directory not found.")

            directory = Directory(
                id=str(uuid.uuid4()),
                name=name,
                inserted_ts=utc_now_str(),
                parent_id=parent_id,
            )
            session.add(directory)
            session.commit()
            return {"ok": True, "directory_id": directory.id}

    def attach_file(self, body: dict) -> dict:
        directory_id = normalize_directory_id(body.get("directory_id"))
        file_hash = str(body.get("sha256_hash", "")).strip().lower()
        if directory_id is None:
            raise ValueError("Choose a real directory before adding a file.")
        if not file_hash:
            raise ValueError("File SHA-256 is required.")

        with Session() as session:
            if not session.get(Directory, directory_id):
                raise ValueError("Directory not found.")
            if not session.get(File, file_hash):
                raise ValueError("File not found in database.")
            self.add_directory_file(session, directory_id, file_hash)
            session.commit()
            return {"ok": True}

    def import_file(self, body: dict) -> dict:
        directory_id = normalize_directory_id(body.get("directory_id"))
        source_path = Path(str(body.get("path", "")).strip()).expanduser()
        name = str(body.get("name", "")).strip() or None
        if directory_id is None:
            raise ValueError("Choose a real directory before importing a file.")
        if not source_path.is_file():
            raise ValueError("Source path must be an existing file.")

        file = create_file(source_path)
        if name is not None:
            file.name = name

        copy_to_storage_if_possible(source_path, file.sha256_hash)

        with Session() as session:
            if not session.get(Directory, directory_id):
                raise ValueError("Directory not found.")

            existing = session.get(File, file.sha256_hash)
            if existing is None:
                session.add(file)
            elif name and not existing.name:
                existing.name = name

            self.add_directory_file(session, directory_id, file.sha256_hash)
            session.commit()
            return {"ok": True, "sha256_hash": file.sha256_hash}

    def attach_bundle(self, body: dict) -> dict:
        directory_id = normalize_directory_id(body.get("directory_id"))
        bundle_id = str(body.get("bundle_id", "")).strip()
        if directory_id is None:
            raise ValueError("Choose a real directory before adding a bundle.")
        if not bundle_id:
            raise ValueError("Bundle id is required.")

        with Session() as session:
            if not session.get(Directory, directory_id):
                raise ValueError("Directory not found.")
            if not session.get(Bundle, bundle_id):
                raise ValueError("Bundle not found in database.")
            self.add_directory_bundle(session, directory_id, bundle_id)
            session.commit()
            return {"ok": True}

    def import_bundle(self, body: dict) -> dict:
        directory_id = normalize_directory_id(body.get("directory_id"))
        source_path = Path(str(body.get("path", "")).strip()).expanduser()
        if directory_id is None:
            raise ValueError("Choose a real directory before importing a bundle.")
        if not source_path.is_dir():
            raise ValueError("Source path must be an existing directory.")

        bundle, files, bundle_files = build_bundle(source_path)

        with Session() as session:
            if not session.get(Directory, directory_id):
                raise ValueError("Directory not found.")

            session.add(bundle)
            for file in files:
                source_file_path = source_path / next(
                    bf.path for bf in bundle_files if bf.file_sha256_hash == file.sha256_hash
                )
                copy_to_storage_if_possible(source_file_path, file.sha256_hash)
                if session.get(File, file.sha256_hash) is None:
                    session.add(file)

            session.flush()
            session.add_all(bundle_files)
            self.add_directory_bundle(session, directory_id, bundle.id)
            session.commit()
            return {"ok": True, "bundle_id": bundle.id, "file_count": len(bundle_files)}

    def move_object(self, body: dict) -> dict:
        kind = str(body.get("kind", ""))
        object_id = str(body.get("id", "")).strip()
        from_directory_id = normalize_directory_id(body.get("from_directory_id"))
        to_directory_id = normalize_directory_id(body.get("to_directory_id"))
        if not object_id:
            raise ValueError("Object id is required.")

        with Session() as session:
            if to_directory_id is not None and not session.get(Directory, to_directory_id):
                raise ValueError("Destination directory not found.")

            if kind == "directory":
                directory = session.get(Directory, object_id)
                if not directory:
                    raise ValueError("Directory not found.")
                if directory.id == to_directory_id:
                    raise ValueError("A directory cannot move into itself.")
                if to_directory_id and is_descendant(session, to_directory_id, directory.id):
                    raise ValueError("A directory cannot move into one of its children.")
                directory.parent_id = to_directory_id

            elif kind == "file":
                if from_directory_id is None or to_directory_id is None:
                    raise ValueError("Files move between real directories.")
                link = session.get(DirectoryFile, (from_directory_id, object_id))
                if not link:
                    raise ValueError("File is not linked from that source directory.")
                session.delete(link)
                self.add_directory_file(session, to_directory_id, object_id)

            elif kind == "bundle":
                if from_directory_id is None or to_directory_id is None:
                    raise ValueError("Bundles move between real directories.")
                link = session.get(DirectoryBundle, (from_directory_id, object_id))
                if not link:
                    raise ValueError("Bundle is not linked from that source directory.")
                session.delete(link)
                self.add_directory_bundle(session, to_directory_id, object_id)
            else:
                raise ValueError("Unknown object kind.")

            session.commit()
            return {"ok": True}

    def remove_object(self, body: dict) -> dict:
        kind = str(body.get("kind", ""))
        object_id = str(body.get("id", "")).strip()
        directory_id = normalize_directory_id(body.get("directory_id"))
        if not object_id:
            raise ValueError("Object id is required.")

        with Session() as session:
            if kind == "file":
                if directory_id is None:
                    raise ValueError("Choose a real directory.")
                link = session.get(DirectoryFile, (directory_id, object_id))
                if link:
                    session.delete(link)
            elif kind == "bundle":
                if directory_id is None:
                    raise ValueError("Choose a real directory.")
                link = session.get(DirectoryBundle, (directory_id, object_id))
                if link:
                    session.delete(link)
            elif kind == "directory":
                delete_directory_tree(session, object_id)
            else:
                raise ValueError("Unknown object kind.")

            session.commit()
            return {"ok": True}

    def delete_directory(self, directory_id: str) -> dict:
        if directory_id in ("", ROOT_ID):
            raise ValueError("Root cannot be deleted.")
        with Session() as session:
            if not session.get(Directory, directory_id):
                raise ValueError("Directory not found.")
            delete_directory_tree(session, directory_id)
            session.commit()
            return {"ok": True}

    def add_directory_file(self, session, directory_id: str, file_hash: str) -> None:
        existing = session.get(DirectoryFile, (directory_id, file_hash))
        if existing:
            return
        session.add(
            DirectoryFile(
                directory_id=directory_id,
                file_sha256_hash=file_hash,
                inserted_ts=utc_now_str(),
            )
        )

    def add_directory_bundle(self, session, directory_id: str, bundle_id: str) -> None:
        existing = session.get(DirectoryBundle, (directory_id, bundle_id))
        if existing:
            return
        session.add(
            DirectoryBundle(
                directory_id=directory_id,
                bundle_id=bundle_id,
                inserted_ts=utc_now_str(),
            )
        )

    def send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Filebase Browser</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f8;
      --panel: #ffffff;
      --line: #d9dee3;
      --text: #1d232a;
      --muted: #66717d;
      --accent: #246bfe;
      --accent-soft: #e8f0ff;
      --danger: #bf2f24;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
    }
    header {
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 {
      margin: 0;
      font-size: 17px;
      font-weight: 650;
      letter-spacing: 0;
    }
    main {
      height: calc(100vh - 52px);
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(420px, 1fr) minmax(280px, 380px);
    }
    aside, section {
      min-width: 0;
      min-height: 0;
      background: var(--panel);
      border-right: 1px solid var(--line);
    }
    .pane-head {
      min-height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 12px;
      border-bottom: 1px solid var(--line);
    }
    .pane-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: .06em;
    }
    .tree, .inspector, .content-scroll {
      height: calc(100% - 44px);
      overflow: auto;
    }
    .tree ul {
      list-style: none;
      margin: 0;
      padding: 6px 0 6px 14px;
    }
    .tree > ul { padding-left: 8px; }
    .tree button, .row {
      width: 100%;
      min-height: 34px;
      display: grid;
      grid-template-columns: 24px minmax(0, 1fr) max-content;
      align-items: center;
      gap: 8px;
      border: 0;
      background: transparent;
      color: var(--text);
      text-align: left;
      padding: 6px 10px;
      cursor: pointer;
    }
    .tree button:hover, .row:hover { background: #f1f4f7; }
    .tree button.active, .row.active { background: var(--accent-soft); color: #164db8; }
    .icon {
      width: 24px;
      height: 24px;
      display: inline-grid;
      place-items: center;
      border-radius: 6px;
      background: #eef1f4;
      color: #52606d;
      font-size: 13px;
      font-weight: 700;
    }
    .name {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .meta {
      color: var(--muted);
      font-size: 12px;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    button, input, select {
      font: inherit;
    }
    .btn {
      min-height: 32px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      padding: 0 10px;
      cursor: pointer;
    }
    .btn:hover { border-color: #b9c2cc; background: #f9fafb; }
    .btn.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
    .btn.danger { color: var(--danger); }
    .btn:disabled { opacity: .45; cursor: default; }
    .search {
      width: min(260px, 100%);
      min-height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
    }
    .rows {
      display: grid;
      grid-auto-rows: minmax(40px, auto);
    }
    .row {
      grid-template-columns: 28px minmax(0, 1fr) 92px 150px;
      border-bottom: 1px solid #edf0f2;
      padding: 8px 12px;
    }
    .row .type {
      color: var(--muted);
      font-size: 12px;
      text-transform: capitalize;
    }
    .inspector {
      padding: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.5;
      color: #26313d;
    }
    dialog {
      width: min(520px, calc(100vw - 24px));
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0;
      box-shadow: 0 20px 70px rgba(26, 33, 42, .25);
    }
    dialog::backdrop { background: rgba(20, 26, 33, .35); }
    .dialog-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    label input, label select {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      color: var(--text);
      font-weight: 400;
    }
    .status {
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    @media (max-width: 900px) {
      main {
        grid-template-columns: 1fr;
        grid-template-rows: 34vh 40vh 1fr;
      }
      aside, section { border-right: 0; border-bottom: 1px solid var(--line); }
      .row { grid-template-columns: 28px minmax(0, 1fr) 72px; }
      .row .date { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Filebase Browser</h1>
    <div class="status" id="status">Ready</div>
  </header>
  <main>
    <aside>
      <div class="pane-head">
        <div class="pane-title">Directories</div>
        <button class="btn" id="refreshBtn" title="Refresh">Refresh</button>
      </div>
      <nav class="tree" id="tree"></nav>
    </aside>

    <section>
      <div class="pane-head">
        <div>
          <div class="pane-title" id="currentTitle">Root</div>
        </div>
        <div class="toolbar">
          <input class="search" id="search" placeholder="Filter contents">
          <button class="btn primary" id="newDirBtn">New Dir</button>
          <button class="btn" id="addFileBtn">Add File</button>
          <button class="btn" id="addBundleBtn">Add Bundle</button>
          <button class="btn" id="moveBtn" disabled>Move</button>
          <button class="btn danger" id="removeBtn" disabled>Remove</button>
        </div>
      </div>
      <div class="content-scroll">
        <div class="rows" id="rows"></div>
      </div>
    </section>

    <section>
      <div class="pane-head">
        <div class="pane-title">Inspector</div>
      </div>
      <pre class="inspector" id="inspector">Select an object to inspect it.</pre>
    </section>
  </main>

  <dialog id="dialog">
    <form method="dialog">
      <div class="dialog-body" id="dialogBody"></div>
      <div class="dialog-actions">
        <button class="btn" value="cancel">Cancel</button>
        <button class="btn primary" id="dialogOk" value="ok">OK</button>
      </div>
    </form>
  </dialog>

  <script>
    const state = {
      tree: null,
      currentDirectoryId: "root",
      currentDirectoryName: "Root",
      items: [],
      selected: null
    };

    const treeEl = document.querySelector("#tree");
    const rowsEl = document.querySelector("#rows");
    const statusEl = document.querySelector("#status");
    const inspectorEl = document.querySelector("#inspector");
    const currentTitleEl = document.querySelector("#currentTitle");
    const searchEl = document.querySelector("#search");
    const moveBtn = document.querySelector("#moveBtn");
    const removeBtn = document.querySelector("#removeBtn");
    const dialog = document.querySelector("#dialog");
    const dialogBody = document.querySelector("#dialogBody");

    function setStatus(message) {
      statusEl.textContent = message;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: {"Content-Type": "application/json"},
        ...options
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Request failed");
      }
      return data;
    }

    async function refreshAll() {
      state.tree = await api("/api/tree");
      renderTree();
      await loadContents(state.currentDirectoryId);
      setStatus("Refreshed");
    }

    async function loadContents(directoryId) {
      const data = await api(`/api/contents?directory_id=${encodeURIComponent(directoryId)}`);
      state.currentDirectoryId = data.directory_id;
      state.currentDirectoryName = data.directory_name;
      state.items = data.items;
      state.selected = null;
      currentTitleEl.textContent = data.directory_name;
      renderTree();
      renderRows();
      updateSelectionActions();
      inspectorEl.textContent = `${data.directory_name}: ${data.items.length} item(s)`;
    }

    function renderTree() {
      if (!state.tree) return;
      treeEl.innerHTML = "";
      const ul = document.createElement("ul");
      ul.appendChild(treeNode({
        id: "root",
        name: "Root",
        children: state.tree.children || []
      }));
      treeEl.appendChild(ul);
    }

    function treeNode(node) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.className = node.id === state.currentDirectoryId ? "active" : "";
      button.innerHTML = `<span class="icon">D</span><span class="name"></span><span class="meta">${(node.children || []).length}</span>`;
      button.querySelector(".name").textContent = node.name;
      button.addEventListener("click", () => loadContents(node.id).catch(showError));
      li.appendChild(button);
      if (node.children && node.children.length) {
        const ul = document.createElement("ul");
        node.children.forEach(child => ul.appendChild(treeNode(child)));
        li.appendChild(ul);
      }
      return li;
    }

    function renderRows() {
      const filter = searchEl.value.trim().toLowerCase();
      rowsEl.innerHTML = "";
      const visible = state.items.filter(item => {
        return !filter ||
          item.name.toLowerCase().includes(filter) ||
          item.kind.toLowerCase().includes(filter) ||
          item.id.toLowerCase().includes(filter);
      });

      if (!visible.length) {
        rowsEl.innerHTML = `<div class="row"><span class="icon">-</span><span class="name">Empty</span><span></span><span class="date"></span></div>`;
        return;
      }

      visible.forEach(item => {
        const row = document.createElement("button");
        row.className = "row" + (state.selected && state.selected.id === item.id && state.selected.kind === item.kind ? " active" : "");
        row.innerHTML = `
          <span class="icon">${item.kind[0].toUpperCase()}</span>
          <span class="name"></span>
          <span class="type">${item.kind}</span>
          <span class="meta date">${item.inserted_ts || ""}</span>
        `;
        row.querySelector(".name").textContent = item.name;
        row.addEventListener("click", () => selectItem(item));
        row.addEventListener("dblclick", () => {
          if (item.kind === "directory") loadContents(item.id).catch(showError);
        });
        rowsEl.appendChild(row);
      });
    }

    async function selectItem(item) {
      state.selected = item;
      renderRows();
      updateSelectionActions();
      const detail = await api(`/api/detail?kind=${encodeURIComponent(item.kind)}&id=${encodeURIComponent(item.id)}`);
      inspectorEl.textContent = JSON.stringify(detail, null, 2);
    }

    function updateSelectionActions() {
      moveBtn.disabled = !state.selected;
      removeBtn.disabled = !state.selected;
    }

    function promptDialog(title, fields) {
      return new Promise(resolve => {
        dialogBody.innerHTML = `<strong>${title}</strong>`;
        fields.forEach(field => {
          const label = document.createElement("label");
          label.textContent = field.label;
          const input = document.createElement(field.type === "select" ? "select" : "input");
          input.name = field.name;
          input.value = field.value || "";
          if (field.placeholder) input.placeholder = field.placeholder;
          if (field.type && field.type !== "select") input.type = field.type;
          if (field.options) {
            field.options.forEach(option => {
              const opt = document.createElement("option");
              opt.value = option.value;
              opt.textContent = option.label;
              input.appendChild(opt);
            });
          }
          label.appendChild(input);
          dialogBody.appendChild(label);
        });
        dialog.onclose = () => {
          if (dialog.returnValue !== "ok") {
            resolve(null);
            return;
          }
          const values = {};
          dialogBody.querySelectorAll("input, select").forEach(input => values[input.name] = input.value);
          resolve(values);
        };
        dialog.showModal();
      });
    }

    async function createDirectory() {
      const values = await promptDialog("New directory", [
        {name: "name", label: "Name", placeholder: "Projects"}
      ]);
      if (!values) return;
      await api("/api/directories", {
        method: "POST",
        body: JSON.stringify({name: values.name, parent_id: state.currentDirectoryId})
      });
      await refreshAll();
      setStatus("Directory created");
    }

    async function addFile() {
      if (state.currentDirectoryId === "root") {
        setStatus("Select a real directory before adding files.");
        return;
      }
      const values = await promptDialog("Add file", [
        {name: "mode", label: "Mode", type: "select", options: [
          {value: "import", label: "Import from local path"},
          {value: "attach", label: "Attach existing SHA-256"}
        ]},
        {name: "path", label: "Path or SHA-256", placeholder: "/path/to/file.txt or hash"},
        {name: "name", label: "Optional display name", placeholder: "Quarterly notes"}
      ]);
      if (!values) return;
      const endpoint = values.mode === "attach" ? "/api/files/attach" : "/api/files/import";
      const payload = values.mode === "attach"
        ? {directory_id: state.currentDirectoryId, sha256_hash: values.path}
        : {directory_id: state.currentDirectoryId, path: values.path, name: values.name};
      await api(endpoint, {method: "POST", body: JSON.stringify(payload)});
      await loadContents(state.currentDirectoryId);
      await refreshAll();
      setStatus("File added");
    }

    async function addBundle() {
      if (state.currentDirectoryId === "root") {
        setStatus("Select a real directory before adding bundles.");
        return;
      }
      const values = await promptDialog("Add bundle", [
        {name: "mode", label: "Mode", type: "select", options: [
          {value: "import", label: "Import from local directory"},
          {value: "attach", label: "Attach existing bundle id"}
        ]},
        {name: "value", label: "Directory path or bundle id", placeholder: "/path/to/folder or UUID"}
      ]);
      if (!values) return;
      const endpoint = values.mode === "attach" ? "/api/bundles/attach" : "/api/bundles/import";
      const payload = values.mode === "attach"
        ? {directory_id: state.currentDirectoryId, bundle_id: values.value}
        : {directory_id: state.currentDirectoryId, path: values.value};
      await api(endpoint, {method: "POST", body: JSON.stringify(payload)});
      await loadContents(state.currentDirectoryId);
      await refreshAll();
      setStatus("Bundle added");
    }

    function flattenDirectories(node, out = []) {
      out.push({value: node.id, label: node.name});
      (node.children || []).forEach(child => flattenDirectories(child, out));
      return out;
    }

    async function moveSelected() {
      if (!state.selected) return;
      const dirs = flattenDirectories({id: "root", name: "Root", children: state.tree.children || []});
      const values = await promptDialog(`Move ${state.selected.name}`, [
        {name: "to", label: "Destination", type: "select", options: dirs}
      ]);
      if (!values) return;
      await api("/api/move", {
        method: "POST",
        body: JSON.stringify({
          kind: state.selected.kind,
          id: state.selected.id,
          from_directory_id: state.currentDirectoryId,
          to_directory_id: values.to
        })
      });
      await refreshAll();
      setStatus("Moved");
    }

    async function removeSelected() {
      if (!state.selected) return;
      const message = state.selected.kind === "directory"
        ? `Delete directory "${state.selected.name}" and all of its children?`
        : `Remove "${state.selected.name}" from this directory?`;
      if (!confirm(message)) return;
      await api("/api/remove", {
        method: "POST",
        body: JSON.stringify({
          kind: state.selected.kind,
          id: state.selected.id,
          directory_id: state.currentDirectoryId
        })
      });
      await refreshAll();
      setStatus("Removed");
    }

    function showError(error) {
      console.error(error);
      setStatus(error.message);
    }

    document.querySelector("#refreshBtn").addEventListener("click", () => refreshAll().catch(showError));
    document.querySelector("#newDirBtn").addEventListener("click", () => createDirectory().catch(showError));
    document.querySelector("#addFileBtn").addEventListener("click", () => addFile().catch(showError));
    document.querySelector("#addBundleBtn").addEventListener("click", () => addBundle().catch(showError));
    moveBtn.addEventListener("click", () => moveSelected().catch(showError));
    removeBtn.addEventListener("click", () => removeSelected().catch(showError));
    searchEl.addEventListener("input", renderRows);

    refreshAll().catch(showError);
  </script>
</body>
</html>
"""


def run(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), FilebaseWebHandler)
    print(f"Filebase web browser running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
