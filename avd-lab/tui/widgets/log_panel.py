"""
AVD Lab TUI - Log Panel Widget

Displays log output with search/filter capabilities.
"""

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
    ListView,
    ListItem,
)


class LogPanel(ModalScreen):
    """
    Modal panel for viewing logs.
    
    Features:
    - Select recent log file from logs directory
    - Live tail toggle
    - Search/filter
    """
    
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("b", "close", "Back"),
        Binding("q", "close", "Back"),
    ]

    DEFAULT_CSS = """
    LogPanel {
        align: center middle;
    }
    
    LogPanel > Container {
        width: 90;
        height: 80;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }
    
    LogPanel .header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        align: center middle;
    }
    
    LogPanel .title {
        text-style: bold;
    }
    
    LogPanel .log-selector {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
    }
    
    LogPanel .search-bar {
        height: 3;
        padding: 0 1;
    }
    
    LogPanel Input {
        width: 1fr;
    }
    
    LogPanel .log-content {
        height: 1fr;
        padding: 0 1;
        overflow-y: scroll;
        background: $surface-darken-3;
    }
    
    LogPanel .log-line {
        margin: 0;
        padding: 0;
    }
    
    LogPanel .log-line.info {
        color: $text;
    }
    
    LogPanel .log-line.warn {
        color: $warning;
    }
    
    LogPanel .log-line.error {
        color: $error;
    }
    
    LogPanel .log-line.debug {
        color: $text-muted;
    }
    
    LogPanel .footer {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        align: center middle;
    }
    
    LogPanel Button {
        margin: 0 1;
    }
    """
    
    # Current log file
    log_file: reactive[Optional[str]] = reactive(None)
    
    # Log content
    log_content: reactive[str] = reactive("")
    
    # Search filter
    search_filter: reactive[str] = reactive("")
    
    # Live tail mode
    live_tail: reactive[bool] = reactive(False)
    
    class CloseRequested(Message):
        """Message sent when panel should close."""
        pass
    
    def __init__(
        self,
        logs_dir: str = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/logs/avd-lab",
        **kwargs
    ):
        super().__init__(**kwargs)
        self._logs_dir = Path(logs_dir)
        self._log_files: list[str] = []
    
    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal(classes="header"):
                yield Label("Log Viewer", classes="title")
            
            with Horizontal(classes="log-selector"):
                yield Label("Log: ", classes="field-label")
                yield Static("", id="current-log")
            
            with Horizontal(classes="search-bar"):
                yield Input(
                    value="",
                    placeholder="Search logs...",
                    id="search-input",
                )
            
            with Container(classes="log-content"):
                yield Static("", id="log-display")
            
            with Horizontal(classes="footer"):
                yield Button("Refresh", id="refresh-btn", variant="primary")
                yield Button("Close", id="close-btn", variant="error")
    
    def on_mount(self) -> None:
        """Initialize on mount."""
        self._load_log_files()
        if self._log_files:
            self.log_file = self._log_files[0]
            self._load_log_content()
    
    def _load_log_files(self) -> None:
        """Load list of log files."""
        if self._logs_dir.exists():
            self._log_files = sorted(
                [str(f) for f in self._logs_dir.glob("*.log")],
                key=lambda x: Path(x).stat().st_mtime,
                reverse=True,
            )
    
    def _load_log_content(self) -> None:
        """Load content of current log file."""
        if self.log_file:
            try:
                path = Path(self.log_file)
                self.log_content = path.read_text(encoding='utf-8', errors='replace')
                self.query_one("#current-log", Static).update(path.name)
            except Exception as e:
                self.log_content = f"Error reading log: {e}"
        else:
            self.log_content = "No log file selected"
        
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the log display."""
        display = self.query_one("#log-display", Static)
        
        lines = self.log_content.split('\n')
        
        # Apply search filter
        if self.search_filter:
            lines = [line for line in lines if self.search_filter.lower() in line.lower()]
        
        # Format lines with styling
        formatted_lines = []
        for line in lines[:500]:  # Limit to 500 lines
            line_lower = line.lower()
            if '"level":"ERROR"' in line_lower or '[error]' in line_lower:
                formatted_lines.append(f"[red]{line}[/red]")
            elif '"level":"WARN"' in line_lower or '[warn]' in line_lower:
                formatted_lines.append(f"[yellow]{line}[/yellow]")
            elif '"level":"DEBUG"' in line_lower or '[debug]' in line_lower:
                formatted_lines.append(f"[dim]{line}[/dim]")
            else:
                formatted_lines.append(line)
        
        display.update('\n'.join(formatted_lines))
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_filter = event.value.strip()
            self._update_display()
    
    
    def action_close(self) -> None:
        """Close this modal."""
        self.dismiss()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            self._load_log_files()
            self._load_log_content()
        elif event.button.id == "close-btn":
            self.dismiss()
    
    def select_log_file(self, log_path: str) -> None:
        """Select a specific log file."""
        self.log_file = log_path
        self._load_log_content()
