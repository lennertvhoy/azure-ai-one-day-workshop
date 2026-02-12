"""
AVD Lab TUI - Template Manager

Manage Lab Configuration Templates (JSON files).
"""

import os
import json
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Label, Input, TextArea, Static, Header, Footer
from textual.widget import Widget
from textual import on

from services.cli_runner import CliRunner

class TemplateEditor(Screen):
    """Screen to edit a template."""
    
    DEFAULT_CSS = """
    TemplateEditor {
        align: center middle;
    }
    
    TemplateEditor > Container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        layout: vertical;
    }
    
    TemplateEditor .header {
        height: 3;
        dock: top;
        align: center middle;
        background: $boost; 
    }
    
    TemplateEditor TextArea {
        height: 1fr;
        border: solid $secondary;
    }
    
    TemplateEditor .footer {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    
    TemplateEditor Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, file_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self._initial_content = ""
        
    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal(classes="header"):
                yield Label(f"Editing: {self.file_path.name}")
            
            yield TextArea.code_editor("", language="json", id="editor")
            
            with Horizontal(classes="footer"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="error")

    def on_mount(self) -> None:
        try:
            content = self.file_path.read_text(encoding="utf-8")
            self._initial_content = content
            self.query_one("#editor", TextArea).text = content
        except Exception as e:
            self.notify(f"Error reading file: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self._save_file()

    def _save_file(self) -> None:
        content = self.query_one("#editor", TextArea).text
        try:
            # Validate JSON
            json.loads(content)
            self.file_path.write_text(content, encoding="utf-8")
            self.notify(f"Saved {self.file_path.name}")
            self.dismiss(True)
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON: {e}", severity="error")
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

class NewTemplateDialog(ModalScreen):
    """Dialog to create a new template (copy)."""
    
    DEFAULT_CSS = """
    NewTemplateDialog {
        align: center middle;
    }
    
    NewTemplateDialog > Container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    NewTemplateDialog Label {
        margin-top: 1;
    }
    
    NewTemplateDialog Input {
        margin-bottom: 1;
    }
    
    NewTemplateDialog .buttons {
        align: center middle;
        margin-top: 1;
        height: 3;
    }
    
    NewTemplateDialog Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, source_template: str, **kwargs):
        super().__init__(**kwargs)
        self.source_template = source_template

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"Create new template from '{self.source_template}'", classes="title")
            yield Label("New Filename:")
            yield Input(id="new-name", placeholder="e.g. lab-custom.json")
            
            with Horizontal(classes="buttons"):
                yield Button("Create", id="create-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            name = self.query_one("#new-name", Input).value
            if name:
                if not name.endswith(".json"):
                    name += ".json"
                self.dismiss(name)

    @on(Input.Submitted, "#new-name")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        self.query_one("#create-btn", Button).press()

class TemplateManager(Screen):
    """
    Screen to manage Templates.
    """
    
    DEFAULT_CSS = """
    TemplateManager {
        align: center middle;
    }
    
    TemplateManager > Container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    TemplateManager .header {
        height: 3;
        dock: top;
        align: center middle; 
    }
    
    TemplateManager DataTable {
        height: 1fr;
        border: solid $secondary;
    }
    
    TemplateManager .footer {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    
    TemplateManager Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "create", "New (Copy)"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, cli_runner: CliRunner, **kwargs):
        super().__init__(**kwargs)
        self._cli = cli_runner
        self._config_dir = Path(cli_runner.CONFIG_DIR)
        
    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal(classes="header"):
                yield Label("Template Manager")
            
            yield DataTable(id="template-table", cursor_type="row", zebra_stripes=True)
            
            with Horizontal(classes="footer"):
                yield Button("New (c)", id="create-btn", variant="success")
                yield Button("Edit (e)", id="edit-btn", variant="primary")
                yield Button("Delete (d)", id="delete-btn", variant="error")
                yield Button("Close (Esc)", id="close-btn", variant="default")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Filename", "Size", "Modified")
        self._load_templates()
        
    def _load_templates(self) -> None:
        table = self.query_one(DataTable)
        table.loading = True
        table.clear()
        
        try:
            if not self._config_dir.exists():
                self._config_dir.mkdir(parents=True, exist_ok=True)
                
            for file in sorted(self._config_dir.glob("*.json")):
                stat = file.stat()
                table.add_row(
                    file.name,
                    f"{stat.st_size} bytes",
                    str(stat.st_mtime) # Format this better?
                )
        except Exception as e:
            self.notify(f"Error listing templates: {e}", severity="error")
            
        table.loading = False

    def action_close(self) -> None:
        self.dismiss()
    
    def _get_selected_file(self) -> Path | None:
        table = self.query_one(DataTable)
        row = table.cursor_row
        if row is not None:
            filename = table.get_row_at(row)[0]
            return self._config_dir / filename
        return None

    def action_edit(self) -> None:
        file_path = self._get_selected_file()
        if file_path:
            self.app.push_screen(TemplateEditor(file_path), lambda res: self._load_templates() if res else None)
            
    def action_create(self) -> None:
        file_path = self._get_selected_file()
        if not file_path:
            self.notify("Select a template to copy from first.", severity="warning")
            return
            
        def handle_create(new_name):
            if new_name:
                new_path = self._config_dir / new_name
                if new_path.exists():
                    self.notify(f"File '{new_name}' already exists!", severity="error")
                    return
                
                try:
                    content = file_path.read_text()
                    new_path.write_text(content)
                    self.notify(f"Created '{new_name}'")
                    self._load_templates()
                except Exception as e:
                    self.notify(f"Error creating file: {e}", severity="error")
        
        self.app.push_screen(NewTemplateDialog(file_path.name), handle_create)

    def action_delete(self) -> None:
        file_path = self._get_selected_file()
        if file_path:
            # Check if it's a default/protected template?
            # Assuming lab-dev.json is protected?
            if file_path.name in ["lab-dev.json", "lab-prod.json"]: # Example protected
                self.notify("Cannot delete default templates.", severity="error")
                return

            try:
                os.remove(file_path)
                self.notify(f"Deleted '{file_path.name}'")
                self._load_templates()
            except Exception as e:
                self.notify(f"Error deleting: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "create-btn":
            self.action_create()
        elif event.button.id == "edit-btn":
            self.action_edit()
        elif event.button.id == "delete-btn":
            self.action_delete()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        # Maybe open edit on select? or just highlight?
        pass
