from textual.app import App, ComposeResult
from textual.widgets import DataTable, TextArea, Button, Input
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual import log

from workers import (
    get_root_directories,
    get_parent_directory,
    get_child_directories,
    get_directory_files,
    rename_directory,
)

from models import DirectoryFile, Directory
from connection import Session


class RenameScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]
    def __init__(self, current_name: str) -> None:
        self.current_name = current_name
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Input(value=self.current_name, placeholder="New name")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class DirectoriesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("l", "enter_directory", "Enter Directory"),
        ("space", "select_directory", "Select Directory"),
        ("r", "rename_directory", "Rename Directory"),
    ]
    directories: reactive[list[Directory]] = reactive(list)
    directory_map: dict[str, Directory] = {}
    selected_directory_ids: reactive[set[str]] = reactive(set)

    class DirectoryEntered(Message):
        def __init__(self, directory: Directory) -> None:
            self.directory = directory
            super().__init__()

    class DirectorySelected(Message):
        def __init__(self, directory: Directory) -> None:
            self.directory = directory
            super().__init__()

    class DirectoryRenamed(Message):
        def __init__(self, directory: Directory, new_name: str) -> None:
            self.directory = directory
            self.new_name = new_name
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
        self.directory_map = {d.id: d for d in self.directories}
        for directory in self.directories:
            self.add_row("", directory.name, key=directory.id)

        self.watch_selected_directory_ids() #SUSPICIOUS JOE

    def action_enter_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory = self.directory_map[cell_key.row_key.value]
        self.post_message(self.DirectoryEntered(directory))

    """
    def action_select_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value
        if directory_id in self.selected_directory_ids:
            self.selected_directory_ids = self.selected_directory_ids - {directory_id}
        else:
            self.selected_directory_ids = self.selected_directory_ids | {directory_id}
    """

    def action_select_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory = self.directory_map[cell_key.row_key.value]
        self.post_message(self.DirectorySelected(directory))

    def action_rename_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory = self.directory_map[cell_key.row_key.value]

        def handle_rename(new_name: str | None) -> None:
            if new_name:
                self.post_message(self.DirectoryRenamed(directory, new_name))

        self.app.push_screen(RenameScreen(directory.name), callback=handle_rename)


class DirectoryFilesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("space", "select_directory_file", "Select Directory File"),
    ]
    directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[set[str]] = reactive(set)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected_col"), ("Name", "name_col"))

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
        directory_file_id = cell_key.row_key.value
        if directory_file_id in self.selected_directory_file_ids:
            self.selected_directory_file_ids = self.selected_directory_file_ids - {
                directory_file_id
            }
        else:
            self.selected_directory_file_ids = self.selected_directory_file_ids | {
                directory_file_id
            }


class FilebaseApp(App):
    BINDINGS = [("h", "parent_directory", "Parent Directory")]
    current_dir: reactive[Directory | None] = reactive(None)
    child_directories: reactive[list[Directory]] = reactive(list)
    child_directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_ids: reactive[set[str]] = reactive(set)

    def action_parent_directory(self) -> None:
        with Session() as session:
            parent_directory = get_parent_directory(self.current_dir, session)
            if parent_directory is None:
                self.current_dir = None
            else:
                self.current_dir = parent_directory

    def on_directories_viewer_directory_entered(
        self, message: DirectoriesViewer.DirectoryEntered
    ) -> None:
        self.current_dir = message.directory

    def on_directories_viewer_directory_selected(self, message: DirectoriesViewer.DirectorySelected) -> None:
        directory_id = message.directory.id
        if directory_id in self.selected_directory_ids:
            self.selected_directory_ids = self.selected_directory_ids - {directory_id}
        else:
            self.selected_directory_ids = self.selected_directory_ids | {directory_id}

    def on_directories_viewer_directory_renamed(
        self, message: DirectoriesViewer.DirectoryRenamed
    ) -> None:
        with Session() as session:
            rename_directory(message.directory, message.new_name, session)

    def watch_current_dir(self) -> None:
        with Session() as session:
            self.child_directories = get_child_directories(self.current_dir, session)

            if self.current_dir is not None:
                self.child_directory_files = get_directory_files(
                    self.current_dir, session
                )
            else:
                self.child_directory_files = []

    def compose(self) -> ComposeResult:
        child_directories_viewer = DirectoriesViewer().data_bind(
            FilebaseApp.selected_directory_ids,
            directories=FilebaseApp.child_directories
        )
        directory_files_viewer = DirectoryFilesViewer().data_bind(
            directory_files=FilebaseApp.child_directory_files
        )
        yield Horizontal(child_directories_viewer, directory_files_viewer)


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()



"""
action_select_directory is outdated. It needs to now post a message so the main app handles it.

"""