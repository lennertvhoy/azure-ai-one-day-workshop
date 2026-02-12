"""
AVD Lab TUI - Jobs Panel

Displays background tasks and their progress.
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Static, DataTable
from textual.widget import Widget
from textual.reactive import reactive

from services.state import Job

class JobsPanel(Widget):
    """
    Panel displaying background jobs.
    """
    
    DEFAULT_CSS = """
    JobsPanel {
        width: 30;
        height: 1fr;
        background: $surface-darken-2;
        border-left: solid $primary;
        padding: 0 1;
        display: none; /* Hidden by default */
    }
    
    JobsPanel .title {
        text-style: bold;
        margin-bottom: 1;
        background: $surface;
        padding: 0 1;
    }
    
    JobsPanel DataTable {
        height: 1fr;
    }
    
    JobsPanel .job-status-running {
        color: $primary;
    }
    
    JobsPanel .job-status-succeeded {
        color: $success;
    }
    
    JobsPanel .job-status-failed {
        color: $error;
    }
    """
    
    jobs: reactive[list[Job]] = reactive([])
    
    def compose(self) -> ComposeResult:
        yield Label("Background Jobs", classes="title")
        yield DataTable(id="jobs-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Task", "Status")
        self._update_table()

    def watch_jobs(self, jobs: list[Job]) -> None:
        self._update_table()

    def _update_table(self) -> None:
        try:
            table = self.query_one(DataTable)
        except Exception:
            return
            
        table.clear()
        for job in self.jobs:
            from rich.text import Text
            
            status_styles = {
                "running": "#89b4fa",    # Blue
                "succeeded": "#a6e3a1",  # Green
                "failed": "#f38ba8",     # Red
                "queued": "#f9e2af"      # Yellow
            }
            color = status_styles.get(job.status, "#cdd6f4")
            
            table.add_row(
                Text(f"{job.type} ({job.target})"),
                Text(job.status, style=color)
            )
