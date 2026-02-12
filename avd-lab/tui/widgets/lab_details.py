"""
AVD Lab TUI - Lab Details Widget

Displays detailed information about a selected lab.
"""

from typing import Optional
import webbrowser
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
        height: auto;
    }
    
    LabDetailsDialog .url-value {
        width: 1fr;
        height: auto;
        color: $accent;
        text-style: underline;
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
                
                if self.lab.workspace_url:
                    yield Label("Access", classes="section-title")
                    with Vertical(classes="info-row-vertical"):
                        yield Label("Virtual Desktop:", classes="label")
                        yield Label(self.lab.workspace_url, classes="url-value")
                
                # Resources (Status-aware)
                yield Label("Resources", classes="section-title")
                self.resource_status = Static("Fetching resource status...", classes="info-row")
                yield self.resource_status
                
                self.session_hosts_table = DataTable(id="session-hosts-table")
                self.session_hosts_table.add_columns("Host Name", "Status")
                self.session_hosts_table.display = False
                yield self.session_hosts_table

            with Horizontal(classes="buttons"):
                if self.lab.workspace_url:
                    yield Button("Open Virtual Desktop (o)", id="open-url-btn", variant="success")
                yield Button("Close (Esc)", id="close-btn", variant="primary")
                yield Button("Destroy (d)", id="destroy-btn", variant="error")
                
    def on_mount(self) -> None:
        """Start fetching detailed status on mount."""
        import asyncio
        asyncio.create_task(self._fetch_detailed_status())

    async def _fetch_detailed_status(self) -> None:
        """Fetch detailed status using avd-lab.sh status."""
        from services.cli_runner import CliRunner
        from services.parser import OutputParser
        
        cli = CliRunner()
        parser = OutputParser()
        
        # This calls avd-lab.sh status --lab-id <lab_id>
        result = await cli.status(lab_id=self.lab.lab_id)
        status_result = parser.parse_status(result.stdout + "\n" + result.stderr)
        
        if status_result.success and status_result.session_hosts:
            self.resource_status.display = False
            self.session_hosts_table.display = True
            self.session_hosts_table.clear()
            for host in status_result.session_hosts:
                self.session_hosts_table.add_row(host.get('name', 'N/A'), host.get('status', 'Unknown'))
        else:
            self.resource_status.update("No active session hosts found or error fetching status.")
                
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
        elif event.button.id == "open-url-btn":
            if self.lab.workspace_url:
                webbrowser.open(self.lab.workspace_url)
