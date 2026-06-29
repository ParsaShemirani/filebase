import sys
import uuid
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import select
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, Tree

from main import build_bundle, create_file, get_current_time_str, Session
from models import Bundle, BundleFile, Directory, DirectoryBundle, DirectoryFile, File


ROOT = "root"


class FilebaseTui(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "toggle_mark", "Mark"),
        ("m", "toggle_mark", "Mark"),
        ("p", "place", "Place"),
        ("x", "mark_directory", "Mark dir"),
        ("n", "prompt_new_directory", "New dir"),
        ("r", "prompt_rename_directory", "Rename dir"),
        ("delete", "delete_directory", "Delete dir"),
        ("a", "prompt_add_file", "Add file"),
        ("b", "prompt_add_bundle", "Add bundle"),
        ("escape", "cancel_prompt", "Cancel"),
    ]

    CSS = """
    #left { width: 30%; }
    #middle { width: 40%; }
    #right { width: 30%; }
    #title { height: 1; }
    #inspector { height: 1fr; }
    #prompt { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.current_directory_id: str | None = None
        self.current_item: tuple[str, str] | None = None
        self.marked: set[tuple[str, str, str]] = set()
        self.marked_directory_id: str | None = None
        self.prompt_mode: str | None = None
        self.rows: list[tuple[str, str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree("Root", data=(ROOT, ROOT), id="left")
            yield DataTable(id="middle")
            with Vertical(id="right"):
                yield Static("Inspector", id="title")
                yield Static("", id="inspector")
                yield Static("", id="prompt_label")
                yield Input(id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.table.cursor_type = "row"
        self.table.add_columns("Mark", "Type", "Name", "Id")
        self.prompt.display = False
        self.load_tree()
        self.load_contents()
        self.update_inspector(ROOT, ROOT)

    @property
    def tree(self) -> Tree:
        return self.query_one("#left", Tree)

    @property
    def table(self) -> DataTable:
        return self.query_one("#middle", DataTable)

    @property
    def inspector(self) -> Static:
        return self.query_one("#inspector", Static)

    @property
    def prompt(self) -> Input:
        return self.query_one("#prompt", Input)

    @property
    def prompt_label(self) -> Static:
        return self.query_one("#prompt_label", Static)

    def load_tree(self) -> None:
        self.tree.clear()
        self.tree.root.data = (ROOT, ROOT)
        self.tree.root.expand()
        with Session() as session:
            self.add_directory_nodes(session, self.tree.root, None)

    def add_directory_nodes(self, session, node, parent_id: str | None) -> None:
        stmt = (
            select(Directory)
            .where(
                Directory.parent_id.is_(None)
                if parent_id is None
                else Directory.parent_id == parent_id
            )
            .order_by(Directory.name, Directory.inserted_ts)
        )
        for directory in session.scalars(stmt):
            child = node.add(directory.name, data=("directory", directory.id))
            self.add_directory_nodes(session, child, directory.id)

    def load_contents(self) -> None:
        self.table.clear(columns=False)
        self.rows = []
        if self.current_directory_id is None:
            return
        with Session() as session:
            file_rows = (
                session.query(DirectoryFile, File)
                .join(File, DirectoryFile.file_sha256_hash == File.sha256_hash)
                .filter(DirectoryFile.directory_id == self.current_directory_id)
                .order_by(File.name, File.extension, File.sha256_hash)
                .all()
            )
            for link, file in file_rows:
                name = file.name or file.sha256_hash
                self.add_middle_row("file", file.sha256_hash, name, link.directory_id)

            bundle_rows = (
                session.query(DirectoryBundle, Bundle)
                .join(Bundle, DirectoryBundle.bundle_id == Bundle.id)
                .filter(DirectoryBundle.directory_id == self.current_directory_id)
                .order_by(Bundle.name, Bundle.inserted_ts)
                .all()
            )
            for link, bundle in bundle_rows:
                self.add_middle_row("bundle", bundle.id, bundle.name, link.directory_id)

    def add_middle_row(self, kind: str, object_id: str, name: str, directory_id: str) -> None:
        mark = "[x]" if (kind, object_id, directory_id) in self.marked else "[ ]"
        self.rows.append((kind, object_id, directory_id))
        self.table.add_row(mark, kind, name, object_id[:12])

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        kind, object_id = event.node.data
        self.current_directory_id = None if object_id == ROOT else object_id
        self.current_item = (kind, object_id)
        self.load_contents()
        self.update_inspector(kind, object_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if 0 <= event.cursor_row < len(self.rows):
            kind, object_id, _ = self.rows[event.cursor_row]
            self.current_item = (kind, object_id)
            self.update_inspector(kind, object_id)

    def update_inspector(self, kind: str, object_id: str) -> None:
        if object_id == ROOT:
            text = "Root\nTop level directories live here."
        else:
            with Session() as session:
                obj = session.get(File, object_id) if kind == "file" else None
                obj = session.get(Bundle, object_id) if kind == "bundle" else obj
                obj = session.get(Directory, object_id) if kind == "directory" else obj
                text = "\n".join(f"{k}: {v}" for k, v in asdict(obj).items()) if obj else ""

                if kind == "bundle" and obj:
                    count = session.query(BundleFile).filter(BundleFile.bundle_id == object_id).count()
                    text += f"\nfiles: {count}"
                if kind == "directory" and obj:
                    child_count = session.query(Directory).filter(Directory.parent_id == object_id).count()
                    file_count = session.query(DirectoryFile).filter(DirectoryFile.directory_id == object_id).count()
                    bundle_count = session.query(DirectoryBundle).filter(DirectoryBundle.directory_id == object_id).count()
                    text += f"\nchild_directories: {child_count}\nfiles: {file_count}\nbundles: {bundle_count}"

        marked = len(self.marked)
        if self.marked_directory_id:
            text += f"\n\nmarked directory: {self.marked_directory_id}"
        if marked:
            text += f"\n\nmarked files/bundles: {marked}"
        self.inspector.update(text)

    def action_toggle_mark(self) -> None:
        row = self.table.cursor_row
        if 0 <= row < len(self.rows):
            item = self.rows[row]
            if item in self.marked:
                self.marked.remove(item)
            else:
                self.marked.add(item)
            self.load_contents()

    def action_mark_directory(self) -> None:
        if self.current_directory_id is not None:
            self.marked_directory_id = self.current_directory_id
            self.update_inspector("directory", self.current_directory_id)

    def action_place(self) -> None:
        with Session() as session:
            with session.begin():
                if self.marked_directory_id:
                    directory = session.get(Directory, self.marked_directory_id)
                    if directory and not self.is_descendant(session, self.marked_directory_id, self.current_directory_id):
                        directory.parent_id = self.current_directory_id
                    self.marked_directory_id = None

                for kind, object_id, from_directory_id in list(self.marked):
                    if self.current_directory_id is None:
                        continue
                    if from_directory_id == self.current_directory_id:
                        continue
                    if kind == "file":
                        old = session.get(DirectoryFile, (from_directory_id, object_id))
                        if old:
                            session.delete(old)
                        if session.get(DirectoryFile, (self.current_directory_id, object_id)) is None:
                            session.add(DirectoryFile(self.current_directory_id, object_id, get_current_time_str()))
                    if kind == "bundle":
                        old = session.get(DirectoryBundle, (from_directory_id, object_id))
                        if old:
                            session.delete(old)
                        if session.get(DirectoryBundle, (self.current_directory_id, object_id)) is None:
                            session.add(DirectoryBundle(self.current_directory_id, object_id, get_current_time_str()))
        self.marked.clear()
        self.load_tree()
        self.load_contents()

    def is_descendant(self, session, directory_id: str, possible_parent_id: str | None) -> bool:
        current = possible_parent_id
        while current is not None:
            if current == directory_id:
                return True
            directory = session.get(Directory, current)
            current = directory.parent_id if directory else None
        return False

    def action_prompt_new_directory(self) -> None:
        self.start_prompt("new_directory", "New directory name")

    def action_prompt_rename_directory(self) -> None:
        self.start_prompt("rename_directory", "New name")

    def action_prompt_add_file(self) -> None:
        self.start_prompt("add_file", "File hash or path")

    def action_prompt_add_bundle(self) -> None:
        self.start_prompt("add_bundle", "Bundle id or directory path")

    def start_prompt(self, mode: str, label: str) -> None:
        self.prompt_mode = mode
        self.prompt_label.update(label)
        self.prompt.value = ""
        self.prompt.display = True
        self.prompt.focus()

    def action_cancel_prompt(self) -> None:
        self.prompt_mode = None
        self.prompt.display = False
        self.prompt_label.update("")
        self.set_focus(self.table)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        mode = self.prompt_mode
        self.action_cancel_prompt()
        if not value:
            return
        if mode == "new_directory":
            self.create_directory(value)
        if mode == "rename_directory":
            self.rename_directory(value)
        if mode == "add_file":
            self.add_file(value)
        if mode == "add_bundle":
            self.add_bundle(value)
        self.load_tree()
        self.load_contents()

    def create_directory(self, name: str) -> None:
        with Session() as session:
            with session.begin():
                session.add(Directory(str(uuid.uuid4()), name, get_current_time_str(), self.current_directory_id))

    def rename_directory(self, name: str) -> None:
        if self.current_directory_id is None:
            return
        with Session() as session:
            with session.begin():
                directory = session.get(Directory, self.current_directory_id)
                if directory:
                    directory.name = name

    def action_delete_directory(self) -> None:
        if self.current_directory_id is None:
            return
        with Session() as session:
            with session.begin():
                self.delete_directory_tree(session, self.current_directory_id)
        self.current_directory_id = None
        self.current_item = (ROOT, ROOT)
        self.load_tree()
        self.load_contents()
        self.update_inspector(ROOT, ROOT)

    def delete_directory_tree(self, session, directory_id: str) -> None:
        child_ids = session.scalars(select(Directory.id).where(Directory.parent_id == directory_id)).all()
        for child_id in child_ids:
            self.delete_directory_tree(session, child_id)
        session.query(DirectoryFile).filter(DirectoryFile.directory_id == directory_id).delete()
        session.query(DirectoryBundle).filter(DirectoryBundle.directory_id == directory_id).delete()
        directory = session.get(Directory, directory_id)
        if directory:
            session.delete(directory)

    def add_file(self, value: str) -> None:
        if self.current_directory_id is None:
            return
        with Session() as session:
            with session.begin():
                path = Path(value).expanduser()
                if path.is_file():
                    file = create_file(path)
                    file.name = path.name
                    if session.get(File, file.sha256_hash) is None:
                        session.add(file)
                    file_hash = file.sha256_hash
                else:
                    file_hash = value
                if session.get(File, file_hash) and session.get(DirectoryFile, (self.current_directory_id, file_hash)) is None:
                    session.add(DirectoryFile(self.current_directory_id, file_hash, get_current_time_str()))

    def add_bundle(self, value: str) -> None:
        if self.current_directory_id is None:
            return
        with Session() as session:
            with session.begin():
                path = Path(value).expanduser()
                if path.is_dir():
                    bundle, files, bundle_files = build_bundle(path)
                    session.add(bundle)
                    seen_hashes: set[str] = set()
                    for file in files:
                        if file.sha256_hash not in seen_hashes and session.get(File, file.sha256_hash) is None:
                            session.add(file)
                        seen_hashes.add(file.sha256_hash)
                    session.add_all(bundle_files)
                    bundle_id = bundle.id
                else:
                    bundle_id = value
                if session.get(Bundle, bundle_id) and session.get(DirectoryBundle, (self.current_directory_id, bundle_id)) is None:
                    session.add(DirectoryBundle(self.current_directory_id, bundle_id, get_current_time_str()))


if __name__ == "__main__":
    sys.exit(FilebaseTui().run())
