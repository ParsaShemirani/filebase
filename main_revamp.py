from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static

from filebase_utils import (
    BrowserItem,
    clone_database,
    create_directory,
    friendly_error,
    get_item_details,
    get_original_database_path,
    get_parent_id,
    get_path,
    list_items,
    move_items,
    replace_database,
    rename_item,
    use_database,
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
        ("e", "edit", "Edit copy"),
        ("w", "write_database", "Write DB"),
        ("u", "discard_edits", "Discard"),
        ("space", "toggle_select", "Select"),
        ("n", "new_directory", "New dir"),
        ("r", "rename", "Rename"),
        ("d", "cut", "Cut"),
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
        self.selected_items: set[BrowserItem] = set()
        self.selected_source_id: str | None = None
        self.cut_items: list[BrowserItem] = []
        self.cut_source_id: str | None = None
        self.prompt_state: PromptState | None = None
        self.working_database_path: Path | None = None

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

    def refresh_view(
        self, message: str | None = None, cursor_row: int | None = None
    ) -> None:
        if self.current_id is None:
            self.left.clear(columns=False)
        else:
            parent_id = get_parent_id(self.current_id)
            self.fill_table(self.left, list_items(parent_id), self.current_id)
        self.rows = list_items(self.current_id)
        self.fill_table(self.middle, self.rows)
        if cursor_row is not None and self.rows:
            self.middle.move_cursor(row=min(cursor_row, len(self.rows) - 1))
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
            if table is self.middle and item in self.selected_items:
                name = f"* {name}"
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
        moving = ""
        if self.cut_items:
            moving = f" | cut: {len(self.cut_items)}"
        elif self.selected_items:
            moving = f" | selected: {len(self.selected_items)}"
        mode = "EDIT" if self.is_editing else "VIEW"
        self.status.update(
            f"{mode} | {get_path(self.current_id)}{moving} | {message or ''}"
        )

    @property
    def is_editing(self) -> bool:
        return self.working_database_path is not None

    def require_editing(self) -> bool:
        if self.is_editing:
            return True
        self.update_status("Press e to edit a temporary copy first")
        return False

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
        self.clear_selection()
        self.refresh_view()

    def action_enter(self) -> None:
        self.enter_selected_directory()

    def enter_selected_directory(self) -> None:
        item = self.selected_item()
        if item is not None and item.kind == "directory":
            self.current_id = item.id
            self.clear_selection()
            self.refresh_view()

    def action_new_directory(self) -> None:
        if not self.require_editing():
            return
        self.start_prompt("new_directory", "New directory name")

    def action_rename(self) -> None:
        if not self.require_editing():
            return
        item = self.selected_item()
        if item is not None:
            self.start_prompt("rename", "New name", item)

    def action_toggle_select(self) -> None:
        if not self.require_editing():
            return
        row = self.middle.cursor_row
        item = self.selected_item()
        if item is None:
            return
        if self.selected_source_id not in (None, self.current_id):
            self.update_status("Selection must come from one directory")
            return

        self.selected_source_id = self.current_id
        if item in self.selected_items:
            self.selected_items.remove(item)
            if not self.selected_items:
                self.selected_source_id = None
        else:
            self.selected_items.add(item)
        self.refresh_view(cursor_row=row + 1)

    def action_cut(self) -> None:
        if not self.require_editing():
            return
        if not self.selected_items:
            return
        self.cut_items = list(self.selected_items)
        self.cut_source_id = self.selected_source_id
        self.selected_items.clear()
        self.selected_source_id = None
        self.refresh_view(f"Cut {len(self.cut_items)} item(s)")

    def action_paste(self) -> None:
        if not self.require_editing():
            return
        if not self.cut_items:
            self.update_status("Nothing is cut")
            return
        try:
            move_items(self.cut_items, self.current_id)
        except Exception as error:
            self.update_status(friendly_error(error))
            return
        moved_count = len(self.cut_items)
        self.cut_items = []
        self.cut_source_id = None
        self.refresh_view(f"Moved {moved_count} item(s)")

    def action_edit(self) -> None:
        if self.is_editing:
            self.update_status("Already editing a copy")
            return
        try:
            self.working_database_path = clone_database()
            use_database(self.working_database_path)
        except Exception as error:
            self.working_database_path = None
            self.update_status(friendly_error(error))
            return
        self.current_id = None
        self.clear_selection()
        self.cut_items = []
        self.cut_source_id = None
        self.refresh_view("Editing temporary copy")

    def action_write_database(self) -> None:
        if self.working_database_path is None:
            self.update_status("No edit copy to write")
            return
        try:
            replace_database(self.working_database_path)
        except Exception as error:
            use_database(self.working_database_path)
            self.update_status(friendly_error(error))
            return
        use_database(get_original_database_path())
        self.working_database_path = None
        self.current_id = None
        self.clear_selection()
        self.cut_items = []
        self.cut_source_id = None
        self.refresh_view("Wrote database")

    def action_discard_edits(self) -> None:
        if self.working_database_path is None:
            self.update_status("No edit copy to discard")
            return
        temp_path = self.working_database_path
        use_database(get_original_database_path())
        temp_path.unlink(missing_ok=True)
        self.working_database_path = None
        self.current_id = None
        self.clear_selection()
        self.cut_items = []
        self.cut_source_id = None
        self.refresh_view("Discarded edit copy")

    def action_quit(self) -> None:
        if self.is_editing:
            self.update_status("Write with w or discard with u before quitting")
            return
        self.exit()

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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table is self.middle:
            self.enter_selected_directory()

    def clear_selection(self) -> None:
        self.selected_items.clear()
        self.selected_source_id = None


if __name__ == "__main__":
    sys.exit(FilebaseTui().run())
