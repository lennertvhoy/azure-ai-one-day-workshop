"""
AVD Lab TUI - Lab Table Widget

Displays a table of active labs with their details.
"""

from datetime import datetime, timezone
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Static, Label

from services.parser import LabListItem


class LabTable(Widget):
    """
    Table widget displaying active labs.
    
    Columns:
    - lab-id
    - participant
    - resource group
    - region
    - expiry
    - status
    """
    
    DEFAULT_CSS = """
    LabTable {
        height: 1fr;
        width: 1fr;
    }
    
    LabTable DataTable {
        height: 1fr;
        width: 1fr;
    }
    
    LabTable .header {
        height: 1;
        width: 1fr;
        background: $surface;
        padding: 0 1;
    }
    
    LabTable .status-running {
        color: $success;
    }
    
    LabTable .status-expired {
        color: $error;
    }
    
    LabTable .status-unknown {
        color: $warning;
    }
    
    LabTable .status-deploying {
        color: $primary;
    }
    """
    
    # Reactive labs list
    labs: reactive[list[LabListItem]] = reactive([])
    
    # Currently selected lab
    selected_lab: reactive[Optional[LabListItem]] = reactive(None)
    
    class LabSelected(Message):
        """Message sent when a lab is selected."""
        def __init__(self, lab: LabListItem) -> None:
            self.lab = lab
            super().__init__()
    
    class RefreshRequested(Message):
        """Message sent when refresh is requested."""
        pass
        
    class LabDetailsRequested(Message):
        """Message sent when lab details are requested."""
        def __init__(self, lab: LabListItem) -> None:
            self.lab = lab
            super().__init__()
    
    def __init__(self, labs: Optional[list[LabListItem]] = None, **kwargs):
        super().__init__(**kwargs)
        self._labs = labs or []
    
    def compose(self) -> ComposeResult:
        yield DataTable(
            id="lab-data-table",
            zebra_stripes=True,
            cursor_type="row",
            show_cursor=True,
        )
    
    def on_mount(self) -> None:
        """Set up the table on mount."""
        table = self.query_one(DataTable)
        table.add_columns(
            "Lab ID", "Participant", "Resource Group", "Region", "Expiry", "Status"
        )
        self._populate_table()
    
    def watch_labs(self, labs: list[LabListItem]) -> None:
        """Update table when labs change."""
        self._labs = labs
        self._populate_table()
    
    def _populate_table(self) -> None:
        """Populate the table with lab data."""
        try:
            table = self.query_one(DataTable)
        except Exception:
            return
        
        table.clear()
        
        for lab in self._labs:
            # Format expiry for display
            expiry_display = self._format_expiry(lab.expiry)
            
            # Create status with styling
            status_text = self._get_status_text(lab.status)
            
            table.add_row(
                lab.lab_id,
                lab.participant,
                lab.resource_group,
                lab.location,
                expiry_display,
                status_text,
            )
    
    def _format_expiry(self, expiry: str) -> str:
        """Format expiry timestamp for display."""
        if expiry == "unknown":
            return "Unknown"
        
        try:
            # Parse ISO 8601 expiry time
            if expiry.endswith('Z'):
                expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            else:
                expiry_dt = datetime.fromisoformat(expiry)
            
            # Format for display
            now = datetime.now(timezone.utc)
            diff = expiry_dt - now
            
            if diff.total_seconds() < 0:
                return "Expired"
            
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            
            if hours > 24:
                days = hours // 24
                return f"{days}d {hours % 24}h"
            else:
                return f"{hours}h {minutes}m"
        except (ValueError, TypeError):
            return expiry
    
    def _get_status_text(self, status: str) -> Text:
        """Get styled status text."""
        status_styles = {
            "running": ("●", "status-running"),
            "expired": ("●", "status-expired"),
            "unknown": ("●", "status-unknown"),
            "deploying": ("◐", "status-deploying"),
        }
        
        icon, style = status_styles.get(status, ("●", "status-unknown"))
        return Text(f"{icon} {status}", style=style)
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row selection."""
        if event.cursor_row is not None and event.cursor_row < len(self._labs):
            self.selected_lab = self._labs[event.cursor_row]
            self.post_message(self.LabSelected(self.selected_lab))
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row double-click/enter."""
        if event.cursor_row is not None and event.cursor_row < len(self._labs):
            self.selected_lab = self._labs[event.cursor_row]
            self.post_message(self.LabDetailsRequested(self.selected_lab))
    
    def get_selected_lab(self) -> Optional[LabListItem]:
        """Get the currently selected lab."""
        return self.selected_lab
    
    def refresh_data(self, labs: list[LabListItem]) -> None:
        """Refresh the table with new data."""
        self.labs = labs
