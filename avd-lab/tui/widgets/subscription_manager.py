"""
AVD Lab TUI - Subscription Manager

Manage Azure subscriptions (list and switch context).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Static
from textual.widget import Widget

from services.cli_runner import CliRunner

class SubscriptionManager(ModalScreen):
    """
    Modal screen to list and switch Azure subscriptions.
    """
    
    DEFAULT_CSS = """
    SubscriptionManager {
        align: center middle;
    }
    
    SubscriptionManager > Container {
        width: 90;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    SubscriptionManager .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        background: $primary;
        color: $text;
        padding: 1;
    }
    
    SubscriptionManager DataTable {
        height: 1fr;
        margin-bottom: 1;
    }
    
    SubscriptionManager .buttons {
        height: 3;
        align: center middle;
    }
    
    SubscriptionManager Button {
        margin: 0 1;
    }
    
    SubscriptionManager .current-sub {
        color: $success;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "select_subscription", "Select"),
    ]
    
    def __init__(self, cli_runner: CliRunner, **kwargs):
        super().__init__(**kwargs)
        self._cli = cli_runner
        self._subscriptions = []
        
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Subscription Manager", classes="title")
            
            yield DataTable(
                id="sub-table", 
                cursor_type="row", 
                zebra_stripes=True
            )
            
            with Horizontal(classes="buttons"):
                yield Button("Select (Enter)", id="select-btn", variant="primary")
                yield Button("Cancel (Esc)", id="cancel-btn", variant="error")
                
    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Subscription ID", "State", "Is Default")
        await self._load_subscriptions()
        
    async def _load_subscriptions(self) -> None:
        self._subscriptions = await self._cli.list_subscriptions()
        
        table = self.query_one(DataTable)
        table.clear()
        
        for sub in self._subscriptions:
            is_default = sub.get("isDefault", False)
            default_marker = "★" if is_default else ""
            
            # Style the row if default? 
            # Textual generic DataTable doesn't support row styling easily based on content 
            # without custom renderables, but we can use the marker.
            
            table.add_row(
                sub.get("name", "Unknown"),
                sub.get("id", "Unknown"),
                sub.get("state", "Unknown"),
                default_marker
            )
            
    def action_close(self) -> None:
        self.dismiss()
        
    def action_select_subscription(self) -> None:
        table = self.query_one(DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        # Wait, getting data back from table row index is cleaner if we track it.
        # But we can assume list order matches if we don't sort.
        # Or safely:
        if table.cursor_row is not None and table.cursor_row < len(self._subscriptions):
            sub = self._subscriptions[table.cursor_row]
            self._switch_subscription(sub)
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.action_close()
        elif event.button.id == "select-btn":
            self.action_select_subscription()
            
    def _switch_subscription(self, sub: dict) -> None:
        sub_id = sub.get("id")
        sub_name = sub.get("name")
        
        if not sub_id:
            return
            
        # Switch context
        import asyncio
        asyncio.create_task(self._do_switch(sub_id, sub_name))
        
    async def _do_switch(self, sub_id: str, sub_name: str) -> None:
        # Show loading or status?
        # Since this is a modal, we might want to close and return the result to App 
        # so App can show the status update.
        self.dismiss({"action": "switch", "id": sub_id, "name": sub_name})
