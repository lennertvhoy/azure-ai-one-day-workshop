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
    u - Manage students
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
from services.state import StateManager, Job
from widgets.lab_table import LabTable
from widgets.create_form import CreateLabForm
from widgets.destroy_confirm import DestroyConfirmDialog
from widgets.validation_view import ValidationView
from widgets.log_panel import LogPanel
from widgets.lab_details import LabDetailsDialog
from widgets.lab_details_pane import LabDetailsPane
from widgets.jobs_panel import JobsPanel
from widgets.subscription_manager import SubscriptionManager
from widgets.rg_manager import ResourceGroupManager
from widgets.template_manager import TemplateManager
from widgets.student_manager import StudentManager
from services.student_service import StudentService


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
        background: #1e1e2e; /* Catppuccin Mocha Base */
        color: #cdd6f4;      /* Catppuccin Mocha Text */
    }
    
    Dashboard .header {
        height: 1;
        background: #89b4fa; /* Catppuccin Blue */
        color: #11111b;
        padding: 0 1;
        text-style: bold;
    }
    
    Dashboard .status-bar {
        height: 1;
        background: #313244;
        padding: 0 1;
        color: #a6adc8;
    }
    
    Dashboard #main-container {
        height: 1fr;
        width: 1fr;
    }
    
    Dashboard .table-container {
        height: 1fr;
        width: 1fr;
    }
    
    Dashboard .output-panel {
        height: 4; /* Minimized by default */
        background: #181825;
        padding: 0 1;
        border-top: solid #89b4fa;
        transition: height 200ms;
    }

    Dashboard .output-panel.expanded {
        height: 15;
    }

    Dashboard #output-scroll {
        height: 1fr;
        overflow-y: auto;
    }
    
    Dashboard .output-title {
        text-style: bold;
        color: #89b4fa;
    }
    
    Dashboard .spinner {
        color: #89b4fa;
    }
    """
    
    BINDINGS = [
        Binding("c", "create_lab", "Create"),
        Binding("d", "destroy_lab", "Destroy"),
        Binding("v", "validate", "Validate"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_link", "Open Link"),
        Binding("l", "toggle_logs", "Toggle Logs"),
        Binding("s", "subscriptions", "Subs"),
        Binding("g", "resource_groups", "RGs"),
        Binding("t", "templates", "Tmpls"),
        Binding("u", "students", "Users"),
        Binding("b", "back", "Back"),
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
            yield Label("Ready", id="status-label")
        
        with Horizontal(id="main-container"):
            with Vertical(classes="table-container"):
                yield LabTable(id="lab-table")
            
            yield LabDetailsPane(id="lab-details-pane")
            yield JobsPanel(id="jobs-panel")
        
        with Container(id="log-panel-container", classes="output-panel"):
            yield Label("Output / Logs", classes="output-title")
            with VerticalScroll(id="output-scroll"):
                yield Static("", id="output-display")
        
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

    def _update_jobs_display(self) -> None:
        """Update jobs panel."""
        try:
            panel = self.query_one("#jobs-panel", JobsPanel)
            panel.jobs = self._state.get_jobs()
            # Auto-show panel if there are active jobs
            active_jobs = [j for j in panel.jobs if j.status in ("queued", "running")]
            panel.display = len(panel.jobs) > 0
        except Exception:
            pass

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
            student_service=self.app.students,
        )

        def handle_create(result) -> None:
            if result and isinstance(result, tuple) and len(result) == 7:
                config_path, participant, ttl, sub_id, rg_mode, rg_name, student_ids = result
                self._do_create(config_path, participant, ttl, sub_id, rg_mode, rg_name, student_ids)

        self.app.push_screen(form, handle_create)
    
    def _do_create(
        self, 
        config_path: str, 
        participant: str, 
        ttl: str,
        subscription_id: Optional[str],
        rg_mode: str,
        rg_name: Optional[str],
        student_ids: Optional[list[str]] = None
    ) -> None:
        """Execute create command with job tracking."""
        job_id = f"create-{participant}-{datetime.now().strftime('%H%M%S')}"
        job = Job(
            id=job_id,
            type="create",
            target=participant,
            status="running",
            start_time=datetime.now().isoformat()
        )
        self._state.add_job(job)
        self._update_jobs_display()
        self._update_status(f"Starting create: {participant}")
        
        # Save config/state
        self._state.set_last_config_path(config_path)
        self._state.add_recent_participant(participant)
        self._state.set_last_ttl(ttl)
        self._state.set_last_subscription_id(subscription_id)
        self._state.set_last_rg_mode(rg_mode)
        if rg_name:
            self._state.add_recent_rg_name(rg_name)
        
        async def run_create():
            start_time = datetime.now()
            
            def log_callback(line: str):
                self._state.update_job(job_id, last_log=line)
                self._update_jobs_display()

            result = await self._cli.create(
                config_path, 
                participant, 
                ttl,
                subscription_id=subscription_id,
                rg_mode=rg_mode,
                rg_name=rg_name,
                student_ids=student_ids,
                on_output=log_callback
            )
            
            end_time = datetime.now()
            duration_str = str(end_time - start_time).split('.')[0]
            
            # Parse result
            create_result = self._parser.parse_create(result.stdout + "\n" + result.stderr)
            
            if create_result.success:
                self._state.update_job(job_id, status="succeeded", duration=duration_str)
                self._update_status(f"Lab created: {create_result.lab_id}")
                if create_result.lab_id:
                    self._state.add_recent_lab_id(create_result.lab_id)
                await self._refresh_labs()
            else:
                self._state.update_job(job_id, status="failed", duration=duration_str, errors=create_result.errors or [result.stderr])
                self._update_status("Create failed")
                self._update_output(f"Job {job_id} failed:\n{result.stderr}")
            
            self._update_jobs_display()
        
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
        """Execute destroy command with job tracking."""
        job_id = f"destroy-{lab_id}-{datetime.now().strftime('%H%M%S')}"
        job = Job(
            id=job_id,
            type="destroy",
            target=lab_id,
            status="running",
            start_time=datetime.now().isoformat()
        )
        self._state.add_job(job)
        self._update_jobs_display()
        self._update_status(f"Destroying {lab_id}...")
        
        async def run_destroy():
            start_time = datetime.now()
            
            def log_callback(line: str):
                self._state.update_job(job_id, last_log=line)
                self._update_jobs_display()

            result = await self._cli.destroy(lab_id=lab_id, on_output=log_callback)
            
            end_time = datetime.now()
            duration_str = str(end_time - start_time).split('.')[0]
            
            destroy_result = self._parser.parse_destroy(result.stdout + "\n" + result.stderr)
            
            if destroy_result.success:
                self._state.update_job(job_id, status="succeeded", duration=duration_str)
                self._update_status(f"Lab destroyed: {lab_id}")
                await self._refresh_labs()
            else:
                self._state.update_job(job_id, status="failed", duration=duration_str, errors=destroy_result.errors or [result.stderr])
                self._update_status("Destroy failed")
                self._update_output(f"Destroy of {lab_id} failed:\n{result.stderr}")
            
            self._update_jobs_display()
        
        asyncio.create_task(run_destroy())
    
    def action_validate(self) -> None:
        """Run validation with job tracking."""
        config_path = self._state.get_last_config_path() or self._cli.DEFAULT_CONFIG
        
        job_id = f"validate-{datetime.now().strftime('%H%M%S')}"
        job = Job(
            id=job_id,
            type="validate",
            target="config",
            status="running",
            start_time=datetime.now().isoformat()
        )
        self._state.add_job(job)
        self._update_jobs_display()
        self._update_status("Running validation...")
        
        async def run_validate():
            start_time = datetime.now()
            result = await self._cli.validate(config_path)
            duration_str = str(datetime.now() - start_time).split('.')[0]
            
            validation_result = self._parser.parse_validation(result.stdout + "\n" + result.stderr)
            
            if validation_result.success:
                self._state.update_job(job_id, status="succeeded", duration=duration_str)
                self._update_status("Validation passed")
            else:
                self._state.update_job(job_id, status="failed", duration=duration_str, errors=validation_result.errors)
                self._update_status("Validation failed")
            
            # Show validation view
            view = ValidationView(result=validation_result, raw_output=result.stdout)
            self.app.push_screen(view)
            self._update_jobs_display()
        
        asyncio.create_task(run_validate())

    def action_refresh(self) -> None:
        """Refresh the lab list with job tracking."""
        job_id = f"refresh-{datetime.now().strftime('%H%M%S')}"
        job = Job(
            id=job_id,
            type="refresh",
            target="all",
            status="running",
            start_time=datetime.now().isoformat()
        )
        self._state.add_job(job)
        self._update_jobs_display()
        self._update_status("Refreshing...")
        
        async def do_refresh():
            start_time = datetime.now()
            await self._refresh_labs()
            duration_str = str(datetime.now() - start_time).split('.')[0]
            
            self._state.update_job(job_id, status="succeeded", duration=duration_str)
            self._update_status(f"Refreshed - {len(self.labs)} labs found")
            self._state.update_refresh_time()
            self._update_jobs_display()
        
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

    def action_students(self) -> None:
        """Open student manager."""
        from widgets.student_manager import StudentManager
        screen = StudentManager(cli_runner=self._cli, student_service=self.app.students)
        self.app.push_screen(screen)

    # === Event handlers ===
    
    def on_lab_table_lab_selected(self, event: LabTable.LabSelected) -> None:
        """Handle lab selection."""
        self.selected_lab = event.lab
        self._update_status(f"Selected: {event.lab.lab_id}")
        # Update detail pane
        try:
            pane = self.query_one("#lab-details-pane", LabDetailsPane)
            pane.lab = event.lab
        except Exception:
            pass

    def on_lab_details_pane_destroy_requested(self, event: LabDetailsPane.DestroyRequested) -> None:
        """Handle destroy request from the side pane."""
        self.action_destroy_lab()

    def action_open_link(self) -> None:
        """Open primary link for selected lab."""
        if not self.selected_lab:
            self.notify("No lab selected", severity="warning")
            return
            
        if self.selected_lab.workspace_url:
            import webbrowser
            import re
            cleaned_url = re.sub(r'\s+', '', self.selected_lab.workspace_url)
            webbrowser.open(cleaned_url)
        else:
            self.notify("No launch link available yet", severity="warning")

    def action_toggle_logs(self) -> None:
        """Toggle log panel expansion."""
        try:
            panel = self.query_one("#log-panel-container")
            panel.toggle_class("expanded")
        except Exception:
            pass
    
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
        self.students = StudentService()
    
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
