from __future__ import annotations

import sys
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static

from filebase_utils import (
    BrowserItem,
    create_directory,
    friendly_error,
    get_item_details,
    get_parent_id,
    get_path,
    list_items,
    move_item,
    rename_item,
)


@dataclass
class PromptState:
    mode: str
    item: BrowserItem | None = None


class FilebaseTui(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("h", "parent", "Parent"),
        ("l", "enter", "Enter"),
        ("enter", "enter", "Enter"),
        ("n", "new_directory", "New dir"),
        ("r", "rename", "Rename"),
        ("m", "mark_move", "Mark move"),
        ("p", "paste", "Paste"),
        ("escape", "cancel_prompt", "Cancel"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #panes { height: 1fr; }
    DataTable { width: 1fr; }
    #middle { border: tall $accent; }
    #status { height: 1; padding: 0 1; }
    #prompt { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.current_id: str | None = None
        self.rows: list[BrowserItem] = []
        self.marked_item: BrowserItem | None = None
        self.prompt_state: PromptState | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panes"):
            yield DataTable(id="left")
            yield DataTable(id="middle")
            yield DataTable(id="right")
        with Vertical(id="prompt"):
            yield Static("", id="status")
            yield Input(id="input")
        yield Footer()

    def on_mount(self) -> None:
        for table in (self.left, self.middle, self.right):
            table.cursor_type = "row"
            table.add_columns("Type", "Name")
        self.input.display = False
        self.middle.focus()
        self.refresh_view("Ready")

    @property
    def left(self) -> DataTable:
        return self.query_one("#left", DataTable)

    @property
    def middle(self) -> DataTable:
        return self.query_one("#middle", DataTable)

    @property
    def right(self) -> DataTable:
        return self.query_one("#right", DataTable)

    @property
    def status(self) -> Static:
        return self.query_one("#status", Static)

    @property
    def input(self) -> Input:
        return self.query_one("#input", Input)

    def refresh_view(self, message: str | None = None) -> None:
        parent_id = get_parent_id(self.current_id)
        self.fill_table(self.left, list_items(parent_id), self.current_id)
        self.rows = list_items(self.current_id)
        self.fill_table(self.middle, self.rows)
        self.refresh_preview()
        self.update_status(message)

    def fill_table(
        self,
        table: DataTable,
        items: list[BrowserItem],
        selected_id: str | None = None,
    ) -> None:
        table.clear(columns=False)
        for item in items:
            name = item.name
            if item.id == selected_id:
                name = f"> {name}"
            table.add_row(self.icon(item), name)

    def refresh_preview(self) -> None:
        self.right.clear(columns=False)
        item = self.selected_item()
        if item is None:
            for key, value in (("path", get_path(self.current_id)), ("items", "0")):
                self.right.add_row(key, value)
            return

        if item.kind == "directory":
            self.fill_table(self.right, list_items(item.id))
            return

        for key, value in get_item_details(item):
            self.right.add_row(key, value)

    def update_status(self, message: str | None = None) -> None:
        marked = ""
        if self.marked_item is not None:
            marked = f" | moving {self.marked_item.kind}: {self.marked_item.name}"
        self.status.update(f"{get_path(self.current_id)}{marked} | {message or ''}")

    def selected_item(self) -> BrowserItem | None:
        row = self.middle.cursor_row
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def icon(self, item: BrowserItem) -> str:
        return "dir" if item.kind == "directory" else "file"

    def action_cursor_down(self) -> None:
        self.middle.action_cursor_down()
        self.refresh_preview()

    def action_cursor_up(self) -> None:
        self.middle.action_cursor_up()
        self.refresh_preview()

    def action_parent(self) -> None:
        self.current_id = get_parent_id(self.current_id)
        self.refresh_view()

    def action_enter(self) -> None:
        item = self.selected_item()
        if item is not None and item.kind == "directory":
            self.current_id = item.id
            self.refresh_view()

    def action_new_directory(self) -> None:
        self.start_prompt("new_directory", "New directory name")

    def action_rename(self) -> None:
        item = self.selected_item()
        if item is not None:
            self.start_prompt("rename", "New name", item)

    def action_mark_move(self) -> None:
        item = self.selected_item()
        if item is not None:
            self.marked_item = item
            self.update_status("Marked for move")

    def action_paste(self) -> None:
        if self.marked_item is None:
            self.update_status("Nothing is marked")
            return
        try:
            move_item(self.marked_item, self.current_id)
        except Exception as error:
            self.update_status(friendly_error(error))
            return
        self.marked_item = None
        self.refresh_view("Moved")

    def start_prompt(
        self, mode: str, placeholder: str, item: BrowserItem | None = None
    ) -> None:
        self.prompt_state = PromptState(mode, item)
        self.input.placeholder = placeholder
        self.input.value = item.name if item is not None else ""
        self.input.display = True
        self.input.focus()

    def action_cancel_prompt(self) -> None:
        self.prompt_state = None
        self.input.display = False
        self.middle.focus()
        self.update_status("Cancelled")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        state = self.prompt_state
        value = event.value
        self.prompt_state = None
        self.input.display = False
        self.middle.focus()
        if state is None:
            return

        try:
            if state.mode == "new_directory":
                create_directory(value, self.current_id)
                message = "Directory created"
            elif state.mode == "rename" and state.item is not None:
                rename_item(state.item, value)
                message = "Renamed"
            else:
                message = "Nothing to do"
        except Exception as error:
            self.refresh_view(friendly_error(error))
            return

        self.refresh_view(message)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table is self.middle:
            self.refresh_preview()


if __name__ == "__main__":
    sys.exit(FilebaseTui().run())
