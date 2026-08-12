from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Input, Label
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual import log

from workers import (
    get_parent_directory,
    get_child_directories,
    get_directory_files,
    generate_directory_path_str,
    rename_directory,
)

from models import DirectoryFile, Directory
from connection import Session


@dataclass
class InfoData:
    current_directory_path_str: str
    selected_directories_count: int
    selected_directory_files_count: int


class InfoDisplay(Label):
    info_data: reactive[InfoData] = reactive(
        InfoData(
            current_directory_path_str="/",
            selected_directories_count=0,
            selected_directory_files_count=0,
        )
    )

    def watch_info_data(self) -> None:
        info_text = (
            f"Current Directory Path: {self.info_data.current_directory_path_str}"
            + " | "
            + f"Selected Directories Count: {self.info_data.selected_directories_count}"
            + " | "
            + f"Selected Directory Files Count: {self.info_data.selected_directory_files_count}"
        )
        self.update(info_text)


class RenameScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, current_name: str) -> None:
        self.current_name = current_name
        super().__init__()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        yield Input(value=self.current_name, placeholder="New name")


class DirectoriesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("l", "enter_directory", "Enter Directory"),
        ("space", "select_directory", "Select Directory"),
        ("r", "rename_directory", "Rename Directory"),
    ]
    directories: reactive[list[Directory]] = reactive(list)
    selected_directory_ids: reactive[set[str]] = reactive(set)

    directories_map: dict[str, Directory] = {}

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

    def watch_directories(self) -> None:
        self.clear()
        self.directories_map = {d.id: d for d in self.directories}
        for directory in self.directories:
            if directory.id in self.selected_directory_ids:
                selected_value = "S"
            else:
                selected_value = ""

            self.add_row(selected_value, directory.name, key=directory.id)

    def watch_selected_directory_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_ids:
                selected_value = "S"
            else:
                selected_value = ""

            self.update_cell(row_key, "selected", selected_value)

    def action_enter_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value
        directory = self.directories_map[directory_id]

        self.post_message(self.DirectoryEntered(directory))

    def action_select_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value
        directory = self.directories_map[directory_id]

        self.post_message(self.DirectorySelected(directory))

    def action_rename_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value
        directory = self.directories_map[directory_id]

        def handle_rename(new_name: str | None) -> None:
            if new_name:
                self.post_message(self.DirectoryRenamed(directory, new_name))

        self.app.push_screen(RenameScreen(directory.name), callback=handle_rename)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected"), ("Name", "name"))


class DirectoryFilesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("space", "select_directory_file", "Select Directory File"),
    ]
    directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[set[str]] = reactive(set)

    directory_files_map: dict[str, Directory] = {}

    class DirectoryFileSelected(Message):
        def __init__(self, directory_file: DirectoryFile) -> None:
            self.directory_file = directory_file
            super().__init__()

    def watch_directory_files(self) -> None:
        self.clear()
        self.directory_files_map = {df.id: df for df in self.directory_files}
        for directory_file in self.directory_files:
            if directory_file.id in self.selected_directory_file_ids:
                selected_value = "S"
            else:
                selected_value = ""

            self.add_row(
                selected_value, directory_file.file_name, key=directory_file.id
            )

    def watch_selected_directory_file_ids(self) -> None:
        for row_key in self.rows:
            if row_key.value in self.selected_directory_file_ids:
                selected_value = "S"
            else:
                selected_value = ""

            self.update_cell(row_key, "selected", selected_value)

    def action_select_directory_file(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_file_id = cell_key.row_key.value
        directory_file = self.directory_files_map[directory_file_id]

        self.post_message(self.DirectoryFileSelected(directory_file))

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected"), ("Name", "name"))


class FilebaseApp(App):
    BINDINGS = [
        ("h", "parent_directory", "Parent Directory"),
        ("d", "deselect_all", "Deselect All"),
    ]
    current_directory: reactive[Directory | None] = reactive(None)

    info_data: reactive[InfoData] = reactive(
        InfoData(
            current_directory_path_str="/",
            selected_directories_count=0,
            selected_directory_files_count=0,
        )
    )

    child_directories: reactive[list[Directory]] = reactive(list)
    selected_directory_ids: reactive[set[str]] = reactive(set)

    directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[set[str]] = reactive(set)

    def watch_current_directory(self) -> None:
        with Session() as session:
            self.info_data.current_directory_path_str = generate_directory_path_str(
                self.current_directory, session
            )
            self.mutate_reactive(FilebaseApp.info_data)

            self.child_directories = get_child_directories(
                self.current_directory, session
            )

            if self.current_directory is not None:
                self.directory_files = get_directory_files(
                    self.current_directory, session
                )
            else:
                self.directory_files = []

    def watch_selected_directory_ids(self) -> None:
        self.info_data.selected_directories_count = len(self.selected_directory_ids)
        self.mutate_reactive(FilebaseApp.info_data)

    def watch_selected_directory_file_ids(self) -> None:
        self.info_data.selected_directory_files_count = len(
            self.selected_directory_file_ids
        )
        self.mutate_reactive(FilebaseApp.info_data)

    def action_parent_directory(self) -> None:
        with Session() as session:
            parent_directory = get_parent_directory(self.current_directory, session)
            if parent_directory is None:
                self.current_directory = None
            else:
                self.current_directory = parent_directory

    def action_deselect_all(self) -> None:
        self.selected_directory_ids = set()
        self.selected_directory_file_ids = set()

    def on_directories_viewer_directory_entered(
        self, message: DirectoriesViewer.DirectoryEntered
    ) -> None:
        self.current_directory = message.directory

    def on_directories_viewer_directory_selected(
        self, message: DirectoriesViewer.DirectorySelected
    ) -> None:
        directory_id = message.directory.id
        self.selected_directory_ids = self.selected_directory_ids ^ {directory_id}

    def on_directories_viewer_directory_renamed(
        self, message: DirectoriesViewer.DirectoryRenamed
    ) -> None:
        with Session() as session:
            rename_directory(message.directory, message.new_name, session)

    def on_directory_files_viewer_directory_file_selected(
        self, message: DirectoryFilesViewer.DirectoryFileSelected
    ) -> None:
        directory_file_id = message.directory_file.id
        self.selected_directory_file_ids = self.selected_directory_file_ids ^ {
            directory_file_id
        }

    def compose(self) -> ComposeResult:
        info_display = InfoDisplay()
        info_display.data_bind(FilebaseApp.info_data)

        child_directories_viewer = DirectoriesViewer()
        child_directories_viewer.data_bind(
            FilebaseApp.selected_directory_ids,
            directories=FilebaseApp.child_directories,
        )

        directory_files_viewer = DirectoryFilesViewer()
        directory_files_viewer.data_bind(
            FilebaseApp.directory_files, FilebaseApp.selected_directory_file_ids
        )

        yield Vertical(
            info_display, Horizontal(child_directories_viewer, directory_files_viewer)
        )


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()
