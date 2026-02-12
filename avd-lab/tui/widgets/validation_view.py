"""
AVD Lab TUI - Validation View Widget

Displays validation results with structured sections and indicators.
"""

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Label,
    Static,
)

from services.parser import ValidationResult


class ValidationView(ModalScreen):
    """
    Modal view for displaying validation results.
    
    Structured sections:
    - Azure auth
    - providers
    - quota check
    - network check
    
    With green/yellow/red indicators.
    Allow copy/export of output.
    """
    
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("b", "close", "Back"),
        Binding("q", "close", "Back"),
    ]

    DEFAULT_CSS = """
    ValidationView {
        align: center middle;
    }
    
    ValidationView > Container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }
    
    ValidationView .header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        align: center middle;
    }
    
    ValidationView .title {
        text-style: bold;
    }
    
    ValidationView .content {
        height: auto;
        max-height: 60;
        padding: 1;
    }
    
    ValidationView .section {
        margin-bottom: 1;
        padding: 1;
        background: $surface-darken-1;
    }
    
    ValidationView .section-title {
        text-style: bold;
        margin-bottom: 0;
    }
    
    ValidationView .check {
        margin-left: 2;
    }
    
    ValidationView .check-ok {
        color: $success;
    }
    
    ValidationView .check-warn {
        color: $warning;
    }
    
    ValidationView .check-error {
        color: $error;
    }
    
    ValidationView .footer {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        align: center middle;
    }
    
    ValidationView Button {
        margin: 0 1;
    }
    """
    
    # Validation result
    result: reactive[Optional[ValidationResult]] = reactive(None)
    
    # Raw output for export
    raw_output: reactive[str] = reactive("")
    
    class CloseRequested(Message):
        """Message sent when view should close."""
        pass
    
    def __init__(
        self,
        result: Optional[ValidationResult] = None,
        raw_output: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self._result = result
        self._raw_output = raw_output
    
    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal(classes="header"):
                yield Label("Validation Results", classes="title")
            
            with VerticalScroll(classes="content"):
                # Azure Auth Section
                with Container(classes="section"):
                    yield Label("Azure Authentication", classes="section-title")
                    yield Static("", id="auth-status", classes="check")
                    yield Static("", id="subscription-status", classes="check")
                
                # Providers Section
                with Container(classes="section"):
                    yield Label("Azure Providers", classes="section-title")
                    yield Static("", id="providers-status", classes="check")
                
                # Quota Section
                with Container(classes="section"):
                    yield Label("Quota Check", classes="section-title")
                    yield Static("", id="quota-status", classes="check")
                
                # Network Section
                with Container(classes="section"):
                    yield Label("Network Check", classes="section-title")
                    yield Static("", id="network-status", classes="check")
                
                # Errors/Warnings
                with Container(classes="section"):
                    yield Label("Issues", classes="section-title")
                    yield Static("", id="issues-status", classes="check")
            
            with Horizontal(classes="footer"):
                yield Button("Close", id="close-btn", variant="primary")
    
    def on_mount(self) -> None:
        """Initialize on mount."""
        self.result = self._result
        self.raw_output = self._raw_output
        self._update_display()
    
    def watch_result(self, result: Optional[ValidationResult]) -> None:
        """Update display when result changes."""
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with validation results."""
        if not self.result:
            return
        
        r = self.result
        
        # Auth status
        auth_status = self.query_one("#auth-status", Static)
        if r.logged_in:
            auth_status.update(f"✓ Logged in as: {r.user_name}")
            auth_status.set_classes("check check-ok")
        else:
            auth_status.update("✗ Not logged in")
            auth_status.set_classes("check check-error")
        
        # Subscription status
        sub_status = self.query_one("#subscription-status", Static)
        if r.subscription_id:
            sub_status.update(f"✓ Subscription: {r.subscription_name} ({r.subscription_id})")
            sub_status.set_classes("check check-ok")
        else:
            sub_status.update("✗ No subscription found")
            sub_status.set_classes("check check-error")
        
        # Providers status
        providers_status = self.query_one("#providers-status", Static)
        if r.providers:
            provider_list = "\n".join([f"  ✓ {p}" for p in r.providers.keys()])
            providers_status.update(f"✓ Providers registered:\n{provider_list}")
            providers_status.set_classes("check check-ok")
        else:
            providers_status.update("⚠ No provider status available")
            providers_status.set_classes("check check-warn")
        
        # Quota status
        quota_status = self.query_one("#quota-status", Static)
        if r.quota_available:
            quota_status.update(f"✓ {r.quota_details}")
            quota_status.set_classes("check check-ok")
        elif r.quota_details:
            quota_status.update(f"⚠ {r.quota_details}")
            quota_status.set_classes("check check-warn")
        else:
            quota_status.update("⚠ Quota check skipped")
            quota_status.set_classes("check check-warn")
        
        # Network status
        network_status = self.query_one("#network-status", Static)
        if r.network_ok:
            network_status.update("✓ No network collisions detected")
            network_status.set_classes("check check-ok")
        else:
            network_status.update("⚠ Network check not performed")
            network_status.set_classes("check check-warn")
        
        # Issues
        issues_status = self.query_one("#issues-status", Static)
        issues = []
        for err in r.errors:
            issues.append(f"✗ ERROR: {err}")
        for warn in r.warnings:
            issues.append(f"⚠ WARN: {warn}")
        
        if issues:
            issues_status.update("\n".join(issues))
            issues_status.set_classes("check check-error" if r.errors else "check check-warn")
        else:
            issues_status.update("✓ No issues found")
            issues_status.set_classes("check check-ok")
    
    
    def action_close(self) -> None:
        """Close this modal."""
        self.dismiss()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss()
    
    def set_result(self, result: ValidationResult, raw_output: str) -> None:
        """Set the validation result."""
        self._result = result
        self._raw_output = raw_output
        self.result = result
        self.raw_output = raw_output
