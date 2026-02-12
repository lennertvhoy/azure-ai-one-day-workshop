"""
AVD Lab TUI - Destroy Confirmation Widget

Modal dialog for confirming lab destruction with explicit confirmation.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
)

from services.parser import LabListItem


class DestroyConfirmDialog(ModalScreen):
    """
    Modal dialog for confirming lab destruction.
    
    Input:
    - selected lab from table OR manual lab-id
    
    Show:
    - lab metadata
    - explicit warning text
    
    Require:
    - typed confirm (DELETE) or equivalent hard confirm
    
    Then execute destroy.
    """
    
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("b", "close", "Back"),
        Binding("q", "close", "Back"),
    ]

    DEFAULT_CSS = """
    DestroyConfirmDialog {
        align: center middle;
    }
    
    DestroyConfirmDialog > Container {
        width: 70;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }
    
    DestroyConfirmDialog .title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    
    DestroyConfirmDialog .lab-info {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
    }
    
    DestroyConfirmDialog .lab-info Label {
        margin-bottom: 0;
    }
    
    DestroyConfirmDialog .warning {
        color: $warning;
        text-style: bold;
        margin: 1 0;
        padding: 1;
        border: solid $warning;
    }
    
    DestroyConfirmDialog .confirm-label {
        margin-top: 1;
    }
    
    DestroyConfirmDialog Input {
        width: 1fr;
        margin-top: 0;
    }
    
    DestroyConfirmDialog .error {
        color: $error;
        margin-top: 0;
    }
    
    DestroyConfirmDialog .buttons {
        margin-top: 1;
        align: center middle;
        height: 3;
    }
    
    DestroyConfirmDialog Button {
        margin: 0 1;
        min-width: 12;
    }
    
    """
    
    # Lab to destroy
    lab: reactive[Optional[LabListItem]] = reactive(None)
    
    # Confirmation input
    confirm_text: reactive[str] = reactive("")
    
    def __init__(self, lab: Optional[LabListItem] = None, **kwargs):
        super().__init__(**kwargs)
        self._lab = lab
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("⚠ Destroy Lab", classes="title")
            
            with Container(classes="lab-info"):
                yield Label("", id="lab-id-display")
                yield Label("", id="participant-display")
                yield Label("", id="resource-group-display")
                yield Label("", id="expiry-display")
            
            yield Static(
                "This action cannot be undone. All resources in the lab will be permanently deleted.",
                classes="warning"
            )
            
            yield Label("Type 'DELETE' to confirm:", classes="confirm-label")
            yield Input(
                value="",
                placeholder="DELETE",
                id="confirm-input",
            )
            yield Static("", id="confirm-error", classes="error")
            
            with Horizontal(classes="buttons"):
                yield Button("Destroy", id="destroy-btn", variant="error", disabled=True)
                yield Button("Cancel", id="cancel-btn", variant="primary")
    
    def on_mount(self) -> None:
        """Initialize dialog on mount."""
        self.lab = self._lab
        self._update_display()
    
    def watch_lab(self, lab: Optional[LabListItem]) -> None:
        """Update display when lab changes."""
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the lab info display."""
        if self.lab:
            self.query_one("#lab-id-display", Label).update(f"Lab ID: {self.lab.lab_id}")
            self.query_one("#participant-display", Label).update(f"Participant: {self.lab.participant}")
            self.query_one("#resource-group-display", Label).update(f"Resource Group: {self.lab.resource_group}")
            self.query_one("#expiry-display", Label).update(f"Expiry: {self.lab.expiry}")
        else:
            self.query_one("#lab-id-display", Label).update("Lab ID: (none selected)")
            self.query_one("#participant-display", Label).update("")
            self.query_one("#resource-group-display", Label).update("")
            self.query_one("#expiry-display", Label).update("")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "confirm-input":
            self.confirm_text = event.value.strip()
            self._validate_confirm()
    
    def _validate_confirm(self) -> None:
        """Validate confirmation text."""
        destroy_btn = self.query_one("#destroy-btn", Button)
        error_widget = self.query_one("#confirm-error", Static)
        
        if self.confirm_text == "DELETE":
            destroy_btn.disabled = False
            error_widget.update("")
        else:
            destroy_btn.disabled = True
            if self.confirm_text:
                error_widget.update("Type 'DELETE' exactly to confirm")
            else:
                error_widget.update("")
    
    
    def action_close(self) -> None:
        """Close this modal."""
        self.dismiss()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "destroy-btn":
            if self.lab and self.confirm_text == "DELETE":
                self.dismiss(self.lab.lab_id)
        elif event.button.id == "cancel-btn":
            self.dismiss()
