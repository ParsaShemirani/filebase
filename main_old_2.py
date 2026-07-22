from dataclasses import dataclass

from textual import events, log
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from handwritten_functions import (
    get_directory_children,
    get_directory_siblings,
    get_root_directory,
)
from connection import Session
from models import File, DirectoryFile, Directory


class ChildDirectoriesViewer(DataTable):
    BINDINGS = [
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
        ("x", "cut", "Cut"),
        ("c", "copy", "Copy"),
        ("w", "wipe_all", "Wipe All")
    ]
    current_dir_id: reactive[str] = reactive(None)
    child_directories: reactive[list[Directory]] = reactive(list)
    selected_directory_ids: reactive[list[str]] = reactive(list)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns(("S", "selected_col"), ("Name", "name_col"))

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

    """
    def on_cut(self) -> None:
        if self.highlighted_directory_id in self.cut_directory_ids:
            self.cut_directory_ids.remove(self.highlighted_directory_id)
        else:
            self.cut_directory_ids.append(self.highlighted_directory_id)
        self.mutate_reactive(ChildDirectoriesViewer.cut_directory_ids)
    """
    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
            )

        for child_directory in child_directories:
            self.child_directories.append(child_directory)


class FilebaseApp(App):
    BINDINGS = [("h", "parent_directory", "Parent Directory")]

    current_dir_id = reactive(None)

    def on_mount(self):
        with Session() as session:
            root_directory = get_root_directory(session=session)
        self.current_dir_id = root_directory.id

    def compose(self) -> ComposeResult:
        yield Horizontal(
            ChildDirectoriesViewer().data_bind(FilebaseApp.current_dir_id)
        )


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()
