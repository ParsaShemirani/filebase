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


class SiblingsViewer(DataTable):
    can_focus = False
    current_dir_id = reactive(None, init=False)

    def on_mount(self):
        self.cursor_type = "none"
        self.add_columns("kind", "name")

    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            sibling_files, sibling_directories, sibling_directory_files = (
                get_directory_siblings(id=value, session=session)
            )

            for sibling_directory in sibling_directories:
                self.add_row("D", sibling_directory.name, key=sibling_directory.id)

            for sibling_directory_file in sibling_directory_files:
                self.add_row(
                    "F",
                    sibling_directory_file.file_name,
                    key=sibling_directory_file.file_name,
                )


class ChildrenViewer(DataTable):
    BINDINGS = [("k", "cursor_up", "Cursor Up"), ("j", "cursor_down", "Cursor Down")]
    current_dir_id = reactive(None)
    selected_file_id = reactive(None)
    selected_directory_id = reactive(None)

    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns("kind", "name")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        if 
        log("JIMMYJONESHIGHLIHGT")
        log(f"{event}")
        james = event.row_key
        log(f"STUPID MAN {james.value}")
        


    def watch_current_dir_id(self, value):
        if value is None:
            return

        with Session() as session:
            child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
            )

        for child_directory in child_directories:
            self.add_row("D", child_directory.name, key=child_directory.id)

        for child_directory_file in child_directory_files:
            self.add_row(
                "F",
                child_directory_file.file_name,
                key=child_directory_file.file_name,
            )


class FilebaseApp(App):
    BINDINGS = [
        ("h", "parent_directory", "Parent Directory"),
        ("l", "enter_directory", "Enter Directory"),
    ]

    current_dir_id = reactive(None)
    selected_file_id = reactive(None)
    selected_directory_id = reactive(None)

    def on_mount(self):
        with Session() as session:
            root_directory = get_root_directory(session=session)
        self.current_dir_id = root_directory.id

    def compose(self) -> ComposeResult:
        yield Horizontal(
            SiblingsViewer().data_bind(FilebaseApp.current_dir_id),
            ChildrenViewer().data_bind(
                FilebaseApp.current_dir_id,
                FilebaseApp.selected_file_id,
                FilebaseApp.selected_directory_id,
            ),
        )


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()
