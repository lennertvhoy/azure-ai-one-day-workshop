"""
AVD Lab TUI - Lab Details Widget

Displays detailed information about a selected lab.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, DataTable
from textual.widget import Widget

from services.parser import LabListItem

class LabDetailsDialog(ModalScreen):
    """
    Modal dialog showing full details for a lab.
    """
    
    DEFAULT_CSS = """
    LabDetailsDialog {
        align: center middle;
    }
    
    LabDetailsDialog > Container {
        width: 80;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    LabDetailsDialog .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        background: $primary;
        color: $text;
        padding: 1;
    }
    
    LabDetailsDialog .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 0; 
        border-bottom: solid $accent;
    }
    
    LabDetailsDialog .info-row {
        height: auto;
        margin-bottom: 0;
    }
    
    LabDetailsDialog .label {
        width: 20;
        text-style: bold;
        color: $text-muted;
    }
    
    LabDetailsDialog .value {
        width: 1fr;
    }
    
    LabDetailsDialog .buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    
    LabDetailsDialog Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("d", "destroy_lab", "Destroy"),
    ]
    
    def __init__(self, lab: LabListItem, **kwargs):
        super().__init__(**kwargs)
        self.lab = lab
        
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"Lab Details: {self.lab.lab_id}", classes="title")
            
            with VerticalScroll():
                # Core Info
                yield Label("Core Information", classes="section-title")
                yield self._create_info_row("Lab ID:", self.lab.lab_id)
                yield self._create_info_row("Participant:", self.lab.participant)
                yield self._create_info_row("Resource Group:", self.lab.resource_group)
                yield self._create_info_row("Location:", self.lab.location)
                yield self._create_info_row("Status:", self.lab.status)
                yield self._create_info_row("Expiry:", self.lab.expiry)
                
                # Resources (Placeholder - could fetch more details via CLI)
                yield Label("Resources", classes="section-title")
                
                # We can't easily get the VM/HostPool details without running 'az resource show' 
                # or 'avd-lab status' again. For now, we show what we have from the list.
                # A future enhancement would be to run `avd-lab.sh status` asynchronously here.
                
                yield Static("More detailed resource information can be viewed by running validation or status check.", classes="info-row")

            with Horizontal(classes="buttons"):
                yield Button("Close (Esc)", id="close-btn", variant="primary")
                yield Button("Destroy (d)", id="destroy-btn", variant="error")
                
    def _create_info_row(self, label: str, value: str) -> Horizontal:
        return Horizontal(
            Label(label, classes="label"),
            Label(value, classes="value"),
            classes="info-row"
        )
            
    def action_close(self) -> None:
        self.dismiss()
        
    def action_destroy_lab(self) -> None:
        self.dismiss("destroy")
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "destroy-btn":
            self.action_destroy_lab()
