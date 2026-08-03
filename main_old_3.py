from dataclasses import dataclass

from textual import events, log
from textual.app import App, ComposeResult
from textual.widgets import DataTable, TextArea, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message

from handwritten_functions import (
    get_directory_children,
    get_directory_siblings,
    get_parent_directory,
    get_root_directories,
    generate_directory_path,
)
from connection import Session
from models import File, DirectoryFile, Directory


class ChildDirectoriesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("l", "enter_directory", "Enter Directory"),
        ("x", "cut", "Cut"),
        ("c", "copy", "Copy"),
        ("w", "wipe_all", "Wipe All"),
    ]
    current_dir_id: reactive[str] = reactive(None)
    child_directories: reactive[list[Directory]] = reactive(list)
    selected_directory_ids: reactive[list[str]] = reactive(list)

    class DirectoryEntered(Message):
        def __init__(self, directory_id: str) -> None:
            self.directory_id = directory_id
            super().__init__()

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected_col"), ("Name", "name_col"))

    def watch_current_dir_id(self, value):
        with Session() as session:
            if value is None:
                child_directories = get_root_directories(session=session)
            else:
                child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
                )
        self.child_directories = child_directories

    def watch_child_directories(self) -> None:
        self.clear()
        for cd in self.child_directories:
            if cd.id in self.selected_directory_ids:
                selected = "S"
            else:
                selected = ""
            self.add_row(selected, cd.name, key=cd.id)

    def action_enter_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        self.post_message(self.DirectoryEntered(cell_key.row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        directory_id = event.row_key.value
        if directory_id in self.selected_directory_ids:
            self.selected_directory_ids.remove(directory_id)
        else:
            self.selected_directory_ids.append(directory_id)
        self.mutate_reactive(ChildDirectoriesViewer.selected_directory_ids)

    def watch_selected_directory_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_ids:
                value = "S"
            else:
                value = ""

            self.update_cell(row_key, "selected_col", value)


class ChildFilesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("x", "cut", "Cut"),
        ("c", "copy", "Copy"),
        ("w", "wipe_all", "Wipe All"),
    ]
    current_dir_id: reactive[str] = reactive(None)
    child_directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[list[str]] = reactive(list)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected_col"), ("Name", "name_col"))

    def watch_current_dir_id(self, value):
        if value is None:
            self.child_directory_files = []
        else:
            with Session() as session:
                child_files, child_directories, child_directory_files = (
                    get_directory_children(id=value, session=session)
                )
                self.child_directory_files = child_directory_files

    def watch_child_directory_files(self) -> None:
        self.clear()
        for cdf in self.child_directory_files:
            if cdf.id in self.selected_directory_file_ids:
                selected = "S"
            else:
                selected = ""
            self.add_row(selected, cdf.file_name, key=cdf.id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        directory_file_id = event.row_key.value
        if directory_file_id in self.selected_directory_file_ids:
            self.selected_directory_file_ids.remove(directory_file_id)
        else:
            self.selected_directory_file_ids.append(directory_file_id)
        self.mutate_reactive(ChildFilesViewer.selected_directory_file_ids)

    def watch_selected_directory_file_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_file_ids:
                value = "S"
            else:
                value = ""

            self.update_cell(row_key, "selected_col", value)


class Status(TextArea):
    current_dir_id: reactive[str] = reactive(None)

    def on_mount(self):
        self.text = ""

    def watch_current_dir_id(self):
        if self.current_dir_id is None:
            self.text = "Main"
        else:
            with Session() as session:
                self.text = generate_directory_path(self.current_dir_id, session)


class FilebaseApp(App):
    BINDINGS = [("h", "parent_directory", "Parent Directory")]

    current_dir_id = reactive(None)

    def on_mount(self):
        self.current_dir_id = None

    def action_parent_directory(self) -> None:
        with Session() as session:
            parent_directory = get_parent_directory(self.current_dir_id, session)
            if parent_directory is None:
                self.current_dir_id = None
            else:
                self.current_dir_id = parent_directory.id

    def on_child_directories_viewer_directory_entered(
        self, message: ChildDirectoriesViewer.DirectoryEntered
    ) -> None:
        self.current_dir_id = message.directory_id

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Status().data_bind(FilebaseApp.current_dir_id),
            Vertical(
                ChildDirectoriesViewer().data_bind(FilebaseApp.current_dir_id),
                ChildFilesViewer().data_bind(FilebaseApp.current_dir_id),
            ),
        )


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()
