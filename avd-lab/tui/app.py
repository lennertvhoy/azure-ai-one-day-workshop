#!/usr/bin/env python3
"""
AVD Lab TUI - Main Application

A terminal UI for managing Azure Virtual Desktop lab environments.

Usage:
    python app.py

Keys:
    c - Create lab
    d - Destroy selected lab
    v - Validate
    r - Refresh
    l - View logs
    q - Quit
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Static,
)

from services.cli_runner import CliRunner, CommandResult
from services.parser import (
    OutputParser,
    LabListItem,
    ValidationResult,
    CreateResult,
    StatusResult,
    DestroyResult,
)
from services.state import StateManager

from widgets.lab_table import LabTable
from widgets.create_form import CreateLabForm
from widgets.destroy_confirm import DestroyConfirmDialog
from widgets.validation_view import ValidationView
from widgets.log_panel import LogPanel
from widgets.lab_details import LabDetailsDialog
from widgets.subscription_manager import SubscriptionManager
from widgets.rg_manager import ResourceGroupManager
from widgets.template_manager import TemplateManager


class Dashboard(Screen):
    """
    Main dashboard screen.
    
    Shows table of labs with actions:
    - c Create
    - d Destroy selected
    - v Validate
    - r Refresh
    - l Logs
    - q Quit
    """
    
    DEFAULT_CSS = """
    Dashboard {
        height: 1fr;
        width: 1fr;
    }
    
    Dashboard .header {
        height: 1;
        background: $primary;
        padding: 0 1;
    }
    
    Dashboard .status-bar {
        height: 1;
        background: $surface-darken-1;
        padding: 0 1;
    }
    
    Dashboard .table-container {
        height: 1fr;
        width: 1fr;
    }
    
    Dashboard .action-bar {
        height: 3;
        background: $surface-darken-1;
        padding: 0 1;
        align: center middle;
    }
    
    Dashboard .output-panel {
        height: 14;
        background: $surface-darken-2;
        padding: 0 1;
        border-top: solid $primary;
    }

    Dashboard #output-scroll {
        height: 1fr;
        overflow-y: auto;
    }
    
    Dashboard .output-title {
        text-style: bold;
        margin-bottom: 0;
    }
    
    Dashboard .spinner {
        color: $primary;
    }
    
    Dashboard Button {
        margin: 0 1;
        min-width: 10;
    }
    """
    
    BINDINGS = [
        Binding("c", "create_lab", "Create"),
        Binding("d", "destroy_lab", "Destroy"),
        Binding("v", "validate", "Validate"),
        Binding("r", "refresh", "Refresh"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "subscriptions", "Subscriptions"),
        Binding("g", "resource_groups", "RGs"),
        Binding("t", "templates", "Templates"),
        Binding("l", "logs", "Logs"),
        Binding("q", "quit", "Quit"),
    ]
    
    # Reactive state
    labs: reactive[list[LabListItem]] = reactive([])
    selected_lab: reactive[Optional[LabListItem]] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    output_text: reactive[str] = reactive("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cli = CliRunner()
        self._parser = OutputParser()
        self._state = StateManager()
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(classes="header"):
            yield Label("AVD Lab Manager")
        
        with Container(classes="status-bar"):
            yield Label("", id="status-label")
        
        with Container(classes="table-container"):
            yield LabTable(id="lab-table")
        
        with Container(classes="output-panel"):
            yield Label("Output", classes="output-title")
            with VerticalScroll(id="output-scroll"):
                yield Static("", id="output-display")
        
        with Horizontal(classes="action-bar"):
            yield Button("Create (c)", id="create-btn", variant="success")
            yield Button("Destroy (d)", id="destroy-btn", variant="error")
            yield Button("Validate (v)", id="validate-btn", variant="primary")
            yield Button("Refresh (r)", id="refresh-btn", variant="primary")
            yield Button("Subs (s)", id="subs-btn", variant="default")
            yield Button("RGs (g)", id="rgs-btn", variant="default")
            yield Button("Tmpl (t)", id="tmpls-btn", variant="default")
            yield Button("Logs (l)", id="logs-btn", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize on mount."""
        self._update_status("Ready")
        # Load labs on mount
        self.action_refresh()
    
    def _update_status(self, message: str) -> None:
        """Update status bar."""
        try:
            label = self.query_one("#status-label", Label)
            label.update(message)
        except Exception:
            pass
    
    def _update_output(self, text: str) -> None:
        """Update output panel."""
        try:
            display = self.query_one("#output-display", Static)
            display.update(text)
        except Exception:
            pass
    

    def _latest_log_file(self) -> str:
        """Return latest avd-lab log path if available."""
        try:
            import glob
            import os
            files = glob.glob(os.path.join(self._cli.LOGS_DIR, "*.log"))
            if not files:
                return ""
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            return files[0]
        except Exception:
            return ""

    def _update_table(self) -> None:
        """Update the lab table."""
        try:
            table = self.query_one("#lab-table", LabTable)
            table.refresh_data(self.labs)
        except Exception as e:
            self._update_output(f"Error updating table: {e}")
    
    # === Actions ===
    
    def action_create_lab(self) -> None:
        """Open create lab dialog."""
        form = CreateLabForm(
            cli_runner=self._cli,
            default_config=self._state.get_last_config_path() or self._cli.DEFAULT_CONFIG,
            recent_participants=self._state.get_recent_participants(),
            last_ttl=self._state.get_last_ttl(),
            last_subscription_id=self._state.get_last_subscription_id(),
            last_rg_mode=self._state.get_last_rg_mode(),
            recent_rg_names=self._state.get_recent_rg_names(),
        )

        def handle_create(result) -> None:
            if result and isinstance(result, tuple) and len(result) == 6:
                config_path, participant, ttl, sub_id, rg_mode, rg_name = result
                self._do_create(config_path, participant, ttl, sub_id, rg_mode, rg_name)

        self.app.push_screen(form, handle_create)
    
    def _do_create(
        self, 
        config_path: str, 
        participant: str, 
        ttl: str,
        subscription_id: Optional[str],
        rg_mode: str,
        rg_name: Optional[str]
    ) -> None:
        """Execute create command."""
        self._update_status("Creating lab...")
        self.is_loading = True
        
        # Save state
        self._state.set_last_config_path(config_path)
        self._state.add_recent_participant(participant)
        self._state.set_last_ttl(ttl)
        self._state.set_last_subscription_id(subscription_id)
        self._state.set_last_rg_mode(rg_mode)
        if rg_name:
            self._state.add_recent_rg_name(rg_name)
        
        async def run_create():
            result = await self._cli.create(
                config_path, 
                participant, 
                ttl,
                subscription_id=subscription_id,
                rg_mode=rg_mode,
                rg_name=rg_name
            )
            
            # Parse result
            create_result = self._parser.parse_create(result.stdout + "\n" + result.stderr)
            
            if create_result.success:
                self._update_status(f"Lab created: {create_result.lab_id}")
                self._update_output(
                    f"Lab ID: {create_result.lab_id}\n"
                    f"Participant: {create_result.participant}\n"
                    f"Resource Group: {create_result.resource_group}\n"
                    f"Expiry: {create_result.expiry}\n\n"
                    f"To destroy: ./avd-lab.sh destroy --lab-id {create_result.lab_id} --yes"
                )
                if create_result.lab_id:
                    self._state.add_recent_lab_id(create_result.lab_id)
                # Refresh the table
                await self._refresh_labs()
            else:
                self._update_status("Create failed")
                self._update_output(f"Error:\n{result.stderr}\n\n{result.stdout}")
            
            self.is_loading = False
        
        asyncio.create_task(run_create())
    
    def action_destroy_lab(self) -> None:
        """Open destroy confirmation dialog."""
        if not self.selected_lab:
            self._update_status("No lab selected")
            return

        dialog = DestroyConfirmDialog(lab=self.selected_lab)

        def handle_destroy(result) -> None:
            if result and isinstance(result, str):
                self._do_destroy(result)

        self.app.push_screen(dialog, handle_destroy)
    
    def _do_destroy(self, lab_id: str) -> None:
        """Execute destroy command."""
        self._update_status(f"Destroying lab {lab_id}...")
        self.is_loading = True
        
        async def run_destroy():
            result = await self._cli.destroy(lab_id=lab_id)
            
            # Parse result
            destroy_result = self._parser.parse_destroy(result.stdout + "\n" + result.stderr)
            
            if destroy_result.success:
                self._update_status(f"Lab destroyed: {lab_id}")
                self._update_output(f"Lab {lab_id} has been destroyed.\n\nCommand: {result.command}")
                # Refresh the table
                await self._refresh_labs()
            else:
                self._update_status("Destroy failed")
                self._update_output(f"Error:\n{result.stderr}\n\n{result.stdout}")
            
            self.is_loading = False
        
        asyncio.create_task(run_destroy())
    
    def action_validate(self) -> None:
        """Run validation and show results."""
        config_path = self._state.get_last_config_path() or self._cli.DEFAULT_CONFIG
        
        self._update_status("Running validation...")
        self.is_loading = True
        
        async def run_validate():
            result = await self._cli.validate(config_path)
            
            # Parse result
            validation_result = self._parser.parse_validation(result.stdout + "\n" + result.stderr)
            
            # Show validation view
            view = ValidationView(result=validation_result, raw_output=result.stdout)
            self.app.push_screen(view)
            
            if validation_result.success:
                self._update_status("Validation passed")
            else:
                self._update_status("Validation failed")
            
            self.is_loading = False
        
        asyncio.create_task(run_validate())
    
    def action_refresh(self) -> None:
        """Refresh the lab list."""
        self._update_status("Refreshing...")
        self.is_loading = True
        
        async def do_refresh():
            await self._refresh_labs()
            self._update_status(f"Refreshed - {len(self.labs)} labs found")
            self._state.update_refresh_time()
            self.is_loading = False
        
        asyncio.create_task(do_refresh())
    
    async def _refresh_labs(self) -> None:
        """Refresh the lab list from Azure."""
        # Use az resource list to get all labs
        try:
            # Run az command directly
            cmd = [
                "az", "resource", "list",
                "--tag", "managed-by=avd-lab-tool",
                "-o", "json"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,  # type: ignore[attr-defined]
                stderr=asyncio.subprocess.PIPE,  # type: ignore[attr-defined]
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8')
                self.labs = self._parser.extract_lab_list(output)
            else:
                self.labs = []
                self._update_output(f"Failed to list labs: {stderr.decode('utf-8')}")
            
            self._update_table()
            
        except Exception as e:
            self._update_output(f"Error refreshing labs: {e}")
            self.labs = []
    
    def action_logs(self) -> None:
        """Open log viewer."""
        panel = LogPanel(logs_dir=self._cli.LOGS_DIR)
        self.app.push_screen(panel)
        
    def action_subscriptions(self) -> None:
        """Open subscription manager."""
        form = SubscriptionManager(cli_runner=self._cli)
        
        def handle_sub_result(result):
            if result and isinstance(result, dict) and result.get("action") == "switch":
                sub_id = result.get("id")
                sub_name = result.get("name")
                self._do_switch_subscription(sub_id, sub_name)
        
        self.app.push_screen(form, handle_sub_result)
        
    def _do_switch_subscription(self, sub_id: str, sub_name: str) -> None:
        """Execute subscription switch."""
        self._update_status(f"Switching to {sub_name}...")
        self.is_loading = True
        
        async def switch():
            success = await self._cli.set_subscription(sub_id)
            if success:
                self._update_status(f"Switched to: {sub_name}")
                self._update_output(f"Switched active subscription to:\n{sub_name}\n({sub_id})")
                # Refresh labs for new sub
                await self._refresh_labs()
            else:
                self._update_status("Failed to switch subscription")
                self._update_output(f"Error: Could not switch to subscription {sub_id}")
            self.is_loading = False
            
        asyncio.create_task(switch())
    
        asyncio.create_task(switch())

    def action_resource_groups(self) -> None:
        """Open resource group manager."""
        screen = ResourceGroupManager(cli_runner=self._cli)
        self.app.push_screen(screen)

    def action_templates(self) -> None:
        """Open template manager."""
        screen = TemplateManager(cli_runner=self._cli)
        self.app.push_screen(screen)

    # === Event handlers ===
    
    def on_lab_table_lab_selected(self, event: LabTable.LabSelected) -> None:
        """Handle lab selection."""
        self.selected_lab = event.lab
        self._update_status(f"Selected: {event.lab.lab_id}")
        
    def on_lab_table_lab_details_requested(self, event: LabTable.LabDetailsRequested) -> None:
        """Handle lab details request."""
        self.selected_lab = event.lab
        
        dialog = LabDetailsDialog(lab=event.lab)
        
        def handle_details(result):
            if result == "destroy":
                self.action_destroy_lab()
                
        self.app.push_screen(dialog, handle_details)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-btn":
            self.action_create_lab()
        elif event.button.id == "destroy-btn":
            self.action_destroy_lab()
        elif event.button.id == "validate-btn":
            self.action_validate()
        elif event.button.id == "refresh-btn":
            self.action_refresh()
        elif event.button.id == "subs-btn":
            self.action_subscriptions()
        elif event.button.id == "rgs-btn":
            self.action_resource_groups()
        elif event.button.id == "tmpls-btn":
            self.action_templates()
        elif event.button.id == "logs-btn":
            self.action_logs()


class AvdLabTui(App):
    """
    AVD Lab TUI Application.
    
    A terminal UI for managing Azure Virtual Desktop lab environments.
    """
    
    CSS_PATH = None  # We use DEFAULT_CSS in screens
    
    SCREENS = {
        "dashboard": Dashboard,
    }
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_mount(self) -> None:
        """Mount the dashboard screen."""
        self.push_screen("dashboard")

    def action_back(self) -> None:
        """Go back from modal if possible."""
        try:
            self.pop_screen()
        except Exception:
            pass


def main():
    """Main entry point."""
    app = AvdLabTui()
    app.run()


if __name__ == "__main__":
    main()
