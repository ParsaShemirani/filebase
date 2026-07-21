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

"""
NOTES:
left: siblings viewer
middle: children viewer
right: selected viewer
"""


class SiblingFilesViewer(DataTable):
    can_focus = False
    current_dir_id = reactive(None, init=False)

    def on_mount(self):
        self.cursor_type = "none"
        self.add_columns("name")

    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            sibling_files, sibling_directories, sibling_directory_files = (
                get_directory_siblings(id=value, session=session)
            )

            for sibling_directory_file in sibling_directory_files:
                self.add_row(
                    sibling_directory_file.file_name, key=sibling_directory_file.id
                )


class SiblingDirectoriesViewer(DataTable):
    can_focus = False
    current_dir_id = reactive(None, init=False)

    def on_mount(self):
        self.cursor_type = "none"
        self.add_columns("name")

    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            sibling_files, sibling_directories, sibling_directory_files = (
                get_directory_siblings(id=value, session=session)
            )

            for sibling_directory in sibling_directories:
                self.add_row(sibling_directory.name, key=sibling_directory.id)


class ChildFilesViewer(DataTable):
    BINDINGS = [("k", "cursor_up", "Cursor Up"), ("j", "cursor_down", "Cursor Down"), ("space", "select_cursor", "Select Cursor")]
    current_dir_id = reactive(None)
    selected_directory_file_ids: reactive[list[str]] = reactive(list)
    cut_directory_file_ids: reactive[list[str]] = reactive(list)
    copied_directory_file_ids: reactive[list[str]] = reactive(list)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns("name")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        directory_file_id = event.row_key.value
        if directory_file_id in self.selected_directory_file_ids:
            return
        self.selected_directory_file_ids.append(directory_file_id)
        self.mutate_reactive(ChildFilesViewer.selected_directory_file_ids)

    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
            )

        for child_directory_file in child_directory_files:
            self.add_row(child_directory_file.file_name, key=child_directory_file.id)


class ChildDirectoriesViewer(DataTable):
    BINDINGS = [("k", "cursor_up", "Cursor Up"), ("j", "cursor_down", "Cursor Down"), ("space", "select_cursor", "Select Cursor")]
    current_dir_id = reactive(None)
    selected_directory_ids: reactive[list[str]] = reactive(list)
    cut_directory_ids: reactive[list[str]] = reactive(list)
    copied_directory_ids: reactive[list[str]] = reactive(list)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns("name")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        directory_id = event.row_key.value
        if directory_id in self.selected_directory_ids:
            return
        self.selected_directory_ids.append(directory_id)
        self.mutate_reactive(ChildFilesViewer.selected_directory_ids)

    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
            )

        for child_directory_file in child_directory_files:
            self.add_row(child_directory_file.file_name, key=child_directory_file.id)


class FilebaseApp(App):
    BINDINGS = [
        ("h", "parent_directory", "Parent Directory"),
        ("l", "enter_directory", "Enter Directory"),
    ]

    current_dir_id = reactive(None)

    def on_mount(self):
        with Session() as session:
            root_directory = get_root_directory(session=session)
        self.current_dir_id = root_directory.id

    def compose(self) -> ComposeResult:
        yield Horizontal(
            SiblingDirectoriesViewer().data_bind(FilebaseApp.current_dir_id),
            ChildFilesViewer().data_bind(FilebaseApp.current_dir_id),
        )


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()