"""
AVD Lab TUI - Lab Details Pane (Non-modal)

Displays detailed information about the selected lab in the dashboard.
"""

import re
from typing import Optional
import webbrowser
from textual.app import ComposeResult
from textual.message import Message
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, Static, DataTable
from textual.widget import Widget
from textual.reactive import reactive

from services.parser import LabListItem, OutputParser
from services.cli_runner import CliRunner

class LabDetailsPane(Widget):
    """
    Side pane showing full details for the selected lab.
    """
    
    DEFAULT_CSS = """
    LabDetailsPane {
        width: 45;
        height: 1fr;
        background: #1e1e2e;
        border-left: solid #313244;
        padding: 1 2;
    }
    
    LabDetailsPane .title {
        text-style: bold;
        margin-bottom: 1;
        color: #89b4fa;
    }
    
    LabDetailsPane .section-title {
        text-style: bold;
        color: #89b4fa;
        margin-top: 1;
        margin-bottom: 0; 
        border-bottom: solid #313244;
    }
    
    LabDetailsPane .info-row {
        height: auto;
        margin-bottom: 0;
    }
    
    LabDetailsPane .label {
        width: 18;
        text-style: bold;
        color: #a6adc8;
    }
    
    LabDetailsPane .value {
        width: 1fr;
        height: auto;
        color: #cdd6f4;
    }
    
    LabDetailsPane .url-value {
        width: 1fr;
        height: 1;
        color: #89b4fa;
        text-style: underline;
        overflow: hidden;
    }
    
    LabDetailsPane .no-lab {
        text-align: center;
        color: #6c7086;
        margin-top: 5;
    }

    LabDetailsPane .buttons {
        height: 3;
        margin-top: 1;
    }
    
    LabDetailsPane Button {
        margin-right: 1;
        min-width: 8;
    }
    """
    
    lab: reactive[Optional[LabListItem]] = reactive(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cli = CliRunner()
        self._parser = OutputParser()

    def compose(self) -> ComposeResult:
        with Vertical(id="details-container"):
            yield Label("Select a lab to view details", id="no-lab-msg", classes="no-lab")
            
            with VerticalScroll(id="content-scroll"):
                # Header
                yield Label("", id="details-lab-id", classes="title")
                
                # Core Info
                yield Label("Core Information", classes="section-title")
                yield self._create_info_row("Participant:", "", id="details-participant")
                yield self._create_info_row("Res Group:", "", id="details-rg")
                yield self._create_info_row("Location:", "", id="details-location")
                yield self._create_info_row("Status:", "", id="details-status")
                yield self._create_info_row("Expiry:", "", id="details-expiry")
                yield self._create_info_row("Host Pool:", "", id="details-hostpool")
                
                # Links
                yield Label("Access", classes="section-title")
                with Vertical(classes="info-row"):
                    yield Label("Virtual Desktop:", classes="label")
                    yield Label("", id="details-url", classes="url-value")
                
                # Resources
                yield Label("Session Hosts", classes="section-title")
                self.resource_status = Static("Pending...", id="details-resource-status")
                yield self.resource_status
                
                self.session_hosts_table = DataTable(id="details-hosts-table")
                self.session_hosts_table.add_columns("Host Name", "Status")
                yield self.session_hosts_table

            with Horizontal(id="details-buttons", classes="buttons"):
                yield Button("Launch (o)", id="pane-open-btn", variant="success")
                yield Button("Destroy (d)", id="pane-destroy-btn", variant="error")

    def on_mount(self) -> None:
        self.query_one("#content-scroll").display = False
        self.query_one("#details-buttons").display = False

    def watch_lab(self, old_lab: Optional[LabListItem], new_lab: Optional[LabListItem]) -> None:
        """Update pane when selected lab changes."""
        if not new_lab:
            self.query_one("#no-lab-msg").display = True
            self.query_one("#content-scroll").display = False
            self.query_one("#details-buttons").display = False
            return

        self.query_one("#no-lab-msg").display = False
        self.query_one("#content-scroll").display = True
        self.query_one("#details-buttons").display = True

        # Update labels
        self.query_one("#details-lab-id", Label).update(f"Lab: {new_lab.lab_id}")
        self.query_one("#details-participant").query_one(".value", Label).update(new_lab.participant)
        self.query_one("#details-rg").query_one(".value", Label).update(new_lab.resource_group)
        self.query_one("#details-location").query_one(".value", Label).update(new_lab.location)
        self.query_one("#details-status").query_one(".value", Label).update(new_lab.status)
        self.query_one("#details-expiry").query_one(".value", Label).update(new_lab.expiry)
        self.query_one("#details-hostpool").query_one(".value", Label).update(new_lab.host_pool or "N/A")
        
        url_label = self.query_one("#details-url", Label)
        if new_lab.workspace_url:
            cleaned_url = re.sub(r'\s+', '', new_lab.workspace_url)
            url_label.update(f"[link={cleaned_url}]{cleaned_url}[/link]")
            url_label.remove_class("text-disabled")
        else:
            url_label.update("No link available")
            url_label.add_class("text-disabled")

        # Fetch detailed status
        import asyncio
        asyncio.create_task(self._fetch_detailed_status(new_lab.lab_id))

    async def _fetch_detailed_status(self, lab_id: str) -> None:
        """Fetch detailed status using avd-lab.sh status."""
        self.resource_status.update("Fetching status...")
        self.resource_status.display = True
        self.session_hosts_table.display = False
        
        result = await self._cli.status(lab_id=lab_id)
        if self.lab and self.lab.lab_id != lab_id:
            return # Lab changed while fetching

        status_result = self._parser.parse_status(result.stdout + "\n" + result.stderr)
        
        if status_result.success and status_result.session_hosts:
            self.resource_status.display = False
            self.session_hosts_table.display = True
            self.session_hosts_table.clear()
            for host in status_result.session_hosts:
                self.session_hosts_table.add_row(host.get('name', 'N/A'), host.get('status', 'Unknown'))
        else:
            self.resource_status.update("No active session hosts found.")
                
    def _create_info_row(self, label: str, value: str, id: str) -> Horizontal:
        return Horizontal(
            Label(label, classes="label"),
            Label(value, classes="value"),
            classes="info-row",
            id=id
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.lab:
            return
            
        if event.button.id == "pane-open-btn":
            if self.lab.workspace_url:
                webbrowser.open(self.lab.workspace_url)
        elif event.button.id == "pane-destroy-btn":
            # We bubble this up to the app
            self.post_message(self.DestroyRequested(self.lab))

    class DestroyRequested(Message):
        """Message sent when destroy is requested from the pane."""
        def __init__(self, lab: LabListItem) -> None:
            self.lab = lab
            super().__init__()
