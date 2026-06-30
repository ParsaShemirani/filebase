from dataclasses import dataclass

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from handwritten_functions import get_directory_children, get_root_directory
from connection import Session

"""
NOTES:
left: siblings viewer
middle: children viewer
right: selected viewer
"""


@dataclass(frozen=True)
class ViewerItem:
    kind: str
    name: str


class ChildrenViewer(DataTable):
    current_dir_id = reactive(None, init=False)

    def on_mount(self):
        self.add_columns("kind", "name")

        with Session() as session:
            root_directory = get_root_directory(session=session)
        self.current_dir_id = root_directory.id

    def watch_current_dir_id(self, value):
        with Session() as session:
            child_files, child_directories, child_directory_files = (
                get_directory_children(id=value, session=session)
            )
            for child_directory in child_directories:
                self.add_row("D", child_directory.name)
            for child_directory_file in child_directory_files:
                self.add_row("F", child_directory_file.file_name)


class FilebaseApp(App):
    BINDINGS = [
        ("h", "parent_directory", "Parent Directory"),
        ("l", "enter_directory", "Enter Directory"),
    ]

    def compose(self) -> ComposeResult:
        yield ChildrenViewer()

    def on_mount(self):
        #self.query_one(ChildrenViewer).current_dir_id = "JAMES"
        #self.query_one(ChildrenViewer).current_dir_id = None
        ...


if __name__ == "__main__":
    app = FilebaseApp()
    app.run()
