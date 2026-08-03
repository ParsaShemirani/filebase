from textual.app import App, ComposeResult
from textual.widgets import DataTable, TextArea, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message

from workers import (
    get_directory_from_id,
    get_root_directories,
    get_parent_directory,
    get_child_directories,
    get_child_directory_files,
)

from models import DirectoryFile, Directory
from connection import Session


class DirectoriesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("l", "enter_directory", "Enter Directory"),
        ("space", "select_directory", "Select Directory"),
    ]
    directories: reactive[list[Directory]] = reactive(list)
    selected_directory_ids: reactive[set[str]] = reactive(set)

    class DirectoryEntered(Message):
        def __init__(self, directory_id: str) -> None:
            self.directory = directory_id
            super().__init__()

    class DirectorySelected(Message):
        def __init__(self, directory_id: str) -> None:
            self.directory = directory_id
            super().__init__()

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected_col"), ("Name", "name_col"))

    def watch_selected_directory_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_ids:
                value = "S"
            else:
                value = ""
            self.update_cell(row_key, "selected_col", value)

    def watch_directories(self) -> None:
        self.clear()
        for directory in self.directories:
            self.add_row("", directory.name, key=directory.id)

        self.watch_selected_directory_ids()

    def action_enter_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        self.post_message(self.DirectoryEntered(cell_key.row_key.value))

    def action_select_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        self.post_message(self.DirectorySelected(cell_key.row_key.value))


class DirectoryFilesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("space", "select_directory_file", "Select Directory File"),
    ]
    directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[set[str]] = reactive(set)

    class DirectoryFileSelected(Message):
        def __init__(self, directory_file_id: str) -> None:
            self.directory_file_id = directory_file_id
            super().__init__()

    def on_mount(self):
        self.cursor_type = "row"
        self.add_column(("S", "selected_col"), ("Name", "name_col"))

    def watch_selected_directory_file_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_file_ids:
                value = "S"
            else:
                value = ""

            self.update_cell(row_key, "selected_col", value)

    def watch_directory_files(self) -> None:
        self.clear()
        for directory_file in self.directory_files:
            self.add_row("", directory_file.file_name, key=directory_file.id)

        self.watch_selected_directory_file_ids()

    def action_select_directory_file(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        self.post_message(self.DirectoryFileSelected(cell_key.row_key.value))
