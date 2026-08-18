from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Input, Label
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual import log

from models import DirectoryFile, Directory
from helpers import FilebaseService


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
            + "\n"
            + f"Selected Directories Count: {self.info_data.selected_directories_count}"
            + " | "
            + f"Selected Directory Files Count: {self.info_data.selected_directory_files_count}"
        )
        self.update(info_text)


class EnterNameScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, initial_name: str, placeholder: str) -> None:
        self.initial_name = initial_name
        self.placeholder = placeholder
        super().__init__()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        yield Input(value=self.initial_name, placeholder=self.placeholder)


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

    class DirectoryEntered(Message):
        def __init__(self, directory_id: str) -> None:
            self.directory_id = directory_id
            super().__init__()

    class DirectorySelected(Message):
        def __init__(self, directory_id: str) -> None:
            self.directory_id = directory_id
            super().__init__()

    class DirectoryRenamed(Message):
        def __init__(self, directory_id: str, new_name: str) -> None:
            self.directory_id = directory_id
            self.new_name = new_name
            super().__init__()

    def watch_directories(self) -> None:
        self.clear()
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

        self.post_message(self.DirectoryEntered(directory_id))

    def action_select_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value

        self.post_message(self.DirectorySelected(directory_id))

    def action_rename_directory(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_id = cell_key.row_key.value
        directory_name = FilebaseService.get_directory_from_id(directory_id).name

        def handle_rename(new_name: str | None) -> None:
            if new_name:
                self.post_message(self.DirectoryRenamed(directory_id, new_name))

        self.app.push_screen(
            EnterNameScreen(directory_name, "Rename Directory"), callback=handle_rename
        )

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected"), ("Name", "name"))


class DirectoryFilesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("space", "select_directory_file", "Select Directory File"),
        ("r", "rename_directory_file", "Rename Directory File"),
    ]
    directory_files: reactive[list[DirectoryFile]] = reactive(list)
    selected_directory_file_ids: reactive[set[str]] = reactive(set)

    directory_files_map: dict[str, DirectoryFile] = {}

    class DirectoryFileSelected(Message):
        def __init__(self, directory_file: DirectoryFile) -> None:
            self.directory_file = directory_file
            super().__init__()

    class DirectoryFileRenamed(Message):
        def __init__(self, directory_file: DirectoryFile, new_name: str) -> None:
            self.directory_file = directory_file
            self.new_name = new_name
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

    def action_rename_directory_file(self) -> None:
        cell_key = self.coordinate_to_cell_key(self.cursor_coordinate)
        directory_file_id = cell_key.row_key.value
        directory_file = self.directory_files_map[directory_file_id]

        def handle_rename(new_name: str | None) -> None:
            if new_name:
                self.post_message(self.DirectoryFileRenamed(directory_file, new_name))

        self.app.push_screen(
            EnterNameScreen(directory_file.file_name, "Rename Directory File"),
            callback=handle_rename,
        )

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected"), ("Name", "name"))


class FilebaseApp(App):
    BINDINGS = [
        ("h", "parent_directory", "Parent Directory"),
        ("d", "deselect_all", "Deselect All"),
        ("x", "cut_paste", "Cut Paste"),
        ("c", "create_directory", "Create Directory"),
    ]
    current_directory_id: reactive[str | None] = reactive(None)

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

    def watch_current_directory_id(self) -> None:
        self.info_data.current_directory_path_str = (
            FilebaseService.generate_directory_path(self.current_directory_id)
        )
        self.mutate_reactive(FilebaseApp.info_data)

        self.child_directories = FilebaseService.get_child_directories(
            self.current_directory_id
        )
        self.directory_files = FilebaseService.get_directory_files(self.current_directory_id)

    def watch_selected_directory_ids(self) -> None:
        self.info_data.selected_directories_count = len(self.selected_directory_ids)
        self.mutate_reactive(FilebaseApp.info_data)

    def watch_selected_directory_file_ids(self) -> None:
        self.info_data.selected_directory_files_count = len(
            self.selected_directory_file_ids
        )
        self.mutate_reactive(FilebaseApp.info_data)

    def action_parent_directory(self) -> None:
        if self.current_directory_id is not None:
            self.current_directory_id = FilebaseService.get_parent_directory(
                self.current_directory_id
            ).id

    def action_deselect_all(self) -> None:
        self.selected_directory_ids = set()
        self.selected_directory_file_ids = set()

    def action_cut_paste(self) -> None:
        if self.current_directory_id is None and self.selected_directory_file_ids == set():
            raise ValueError("Attempted to move directory files to None directory, aborted")

        FilebaseService.cut_paste_directories(
            self.selected_directory_ids, self.current_directory_id
        )
        FilebaseService.cut_paste_directory_files(
            self.selected_directory_file_ids, self.current_directory_id
        )

    def action_create_directory(self) -> None:
        def handle_create_directory(name: str | None) -> None:
            if name:
                FilebaseService.create_directory(name, self.current_directory_id)

        self.push_screen(
            EnterNameScreen("", "Create Directory"), callback=handle_create_directory
        )

    def on_directories_viewer_directory_entered(
        self, message: DirectoriesViewer.DirectoryEntered
    ) -> None:
        self.current_directory_id = message.directory_id

    def on_directories_viewer_directory_selected(
        self, message: DirectoriesViewer.DirectorySelected
    ) -> None:
        self.selected_directory_ids = self.selected_directory_ids ^ {message.directory_id}

    def on_directories_viewer_directory_renamed(
        self, message: DirectoriesViewer.DirectoryRenamed
    ) -> None:
        FilebaseService.rename_directory(message.directory_id, message.new_name)

    def on_directory_files_viewer_directory_file_selected(
        self, message: DirectoryFilesViewer.DirectoryFileSelected
    ) -> None:
        directory_file_id = message.directory_file.id
        self.selected_directory_file_ids = self.selected_directory_file_ids ^ {
            directory_file_id
        }

    def on_directory_files_viewer_directory_file_renamed(
        self, message: DirectoryFilesViewer.DirectoryFileRenamed
    ) -> None:
        FilebaseService.rename_directory_file(
            message.directory_file.id, message.new_name
        )

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
