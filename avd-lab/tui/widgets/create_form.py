"""
AVD Lab TUI - Create Lab Form Widget

Form for creating new labs with validation and preview.
"""

import re
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
    Select,
    RadioButton,
    RadioSet,
    DataTable,
)
from textual.containers import Grid

from services.cli_runner import CliRunner
from services.student_service import StudentService


class CreateLabForm(ModalScreen):
    """
    Modal form for creating a new lab.
    
    Fields:
    - config path (default prefilled absolute path)
    - participant slug (required, validated)
    - TTL (8h default)
    - optional course override (advanced)
    
    Preview panel:
    - generated lab-id format
    - command preview
    - safety warnings
    
    Buttons:
    - Create
    - Cancel
    """
    
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("b", "close", "Back"),
        Binding("q", "close", "Back"),
    ]

    DEFAULT_CSS = """
    CreateLabForm {
        align: center middle;
    }
    
    CreateLabForm > Container {
        width: 80;
        height: 90%;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    CreateLabForm #form-scroll {
        height: 1fr;
        overflow-y: auto;
    }
    
    CreateLabForm .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    CreateLabForm .field-label {
        margin-top: 1;
        margin-bottom: 0;
    }
    
    CreateLabForm Input {
        width: 1fr;
        margin-bottom: 0;
    }
    
    CreateLabForm Select {
        width: 1fr;
        margin-bottom: 0;
    }
    
    CreateLabForm .preview {
        margin-top: 1;
        padding: 1;
        background: $surface-darken-1;
        border: solid $primary;
    }
    
    CreateLabForm .preview-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    CreateLabForm .warning {
        color: $warning;
        margin-top: 1;
    }
    
    CreateLabForm .error {
        color: $error;
        margin-top: 0;
    }
    
    CreateLabForm .success {
        color: $success;
        margin-top: 0;
    }
    
    CreateLabForm .buttons {
        margin-top: 1;
        align: center middle;
        height: 3;
    }
    
    CreateLabForm Button {
        margin: 0 1;
        min-width: 12;
    }
    
    """
    
    # Form values
    config_path: reactive[str] = reactive("")
    participant: reactive[str] = reactive("")
    ttl: reactive[str] = reactive("8h")
    subscription_id: reactive[Optional[str]] = reactive(None)
    rg_mode: reactive[str] = reactive("new_per_lab")
    rg_name: reactive[Optional[str]] = reactive(None)
    student_ids: reactive[list[str]] = reactive([])
    
    # Validation state
    participant_valid: reactive[bool] = reactive(False)
    config_valid: reactive[bool] = reactive(False)
    ttl_valid: reactive[bool] = reactive(True)
    subscription_valid: reactive[bool] = reactive(True) # Optional normally, but checked if selected
    rg_valid: reactive[bool] = reactive(True)
    
    def __init__(
        self,
        cli_runner: CliRunner,
        default_config: str = "",
        recent_participants: Optional[list[str]] = None,
        last_ttl: str = "8h",
        last_subscription_id: Optional[str] = None,
        last_rg_mode: str = "new_per_lab",
        recent_rg_names: Optional[list[str]] = None,
        student_service: Optional[StudentService] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._cli = cli_runner
        self._students = student_service
        self._default_config = default_config
        self._recent_participants = recent_participants or []
        self._last_ttl = last_ttl
        self._last_subscription_id = last_subscription_id
        self._last_rg_mode = last_rg_mode
        self._recent_rg_names = recent_rg_names or []
        
        self.rg_mode = last_rg_mode
        self.subscription_id = last_subscription_id
    
    def compose(self) -> ComposeResult:
        with Container():
            with VerticalScroll(id="form-scroll"):
                yield Label("Create New Lab", classes="title")

                yield Label("Config Path:", classes="field-label")
                yield Input(
                    value=self._default_config,
                    placeholder="/absolute/path/to/config.json",
                    id="config-input",
                )
                yield Static("", id="config-error", classes="error")

                yield Label("Participant Slug:", classes="field-label")
                yield Input(
                    value="",
                    placeholder="lowercase alphanumeric and hyphens only",
                    id="participant-input",
                )
                yield Static("", id="participant-error", classes="error")

                yield Label("TTL (Time-to-Live):", classes="field-label")
                yield Select(
                    options=[
                        ("4 hours", "4h"),
                        ("8 hours", "8h"),
                        ("12 hours", "12h"),
                        ("24 hours (1 day)", "1d"),
                        ("48 hours (2 days)", "2d"),
                    ],
                    value=self._last_ttl,
                    id="ttl-select",
                )

                yield Label("Subscription:", classes="field-label")
                yield Select(
                    options=[],
                    prompt="Loading subscriptions...",
                    id="subscription-select",
                )
                
                yield Label("Resource Group Strategy:", classes="field-label")
                with RadioSet(id="rg-mode-radios"):
                    yield RadioButton("Create new RG per lab (Recommended)", value="new_per_lab", id="mode-new")
                    yield RadioButton("Use existing RG", value="existing", id="mode-existing")
                
                yield Label("Resource Group:", classes="field-label", id="rg-name-label")
                yield Select(
                    options=[],
                    prompt="Select Resource Group...",
                    id="rg-name-select",
                    classes="hidden"
                )
                yield Static("", id="rg-error", classes="error")

                yield Label("Assigned Students:", classes="field-label")
                yield DataTable(id="students-selection-table", cursor_type="row", zebra_stripes=True)
                yield Static("Select students by clicking/Enter (Space toggles)", id="student-help")

                with Container(classes="preview"):
                    yield Label("Preview", classes="preview-title")
                    yield Static("", id="preview-lab-id")
                    yield Static("", id="preview-command")

                yield Static("", id="warning-text", classes="warning")

                with Horizontal(classes="buttons"):
                    yield Button("Create", id="create-btn", variant="success")
                    yield Button("Cancel", id="cancel-btn", variant="error")
    
    def on_mount(self) -> None:
        """Initialize form on mount."""
        self.config_path = self._default_config
        self.ttl = self._last_ttl
        
        # Set initial RG mode
        if self._last_rg_mode == "existing":
            self.query_one("#mode-existing", RadioButton).value = True
        else:
            self.query_one("#mode-new", RadioButton).value = True
            
        self._toggle_rg_picker(self._last_rg_mode == "existing")
        
        self._validate_all()
        self._update_preview()
        
        # Load data
        import asyncio
        asyncio.create_task(self._load_subscriptions())
        self._load_students()
    
    def _load_students(self) -> None:
        """Load students from service."""
        table = self.query_one("#students-selection-table", DataTable)
        table.add_columns("?", "Email")
        if self._students:
            for student in self._students.get_students():
                table.add_row("☐", student.email)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle student selection."""
        if event.data_table.id == "students-selection-table":
            table = event.data_table
            row = table.get_row_at(event.cursor_coordinate.row)
            email = row[1]
            status = row[0]
            
            new_status = "☑" if status == "☐" else "☐"
            table.update_cell_at(event.cursor_coordinate, new_status)
            
            if new_status == "☑":
                # Get Object ID
                obj_id = self._students.get_object_id_by_email(email)
                if obj_id and obj_id not in self.student_ids:
                    self.student_ids.append(obj_id)
            else:
                obj_id = self._students.get_object_id_by_email(email)
                if obj_id in self.student_ids:
                    self.student_ids.remove(obj_id)
            
            self._update_preview()

    async def _load_subscriptions(self) -> None:
        """Load subscriptions from Azure."""
        subs = await self._cli.list_subscriptions()
        
        options = []
        for sub in subs:
            name = sub.get('name', 'Unknown')
            sid = sub.get('id', '')
            label = f"{name} ({sid})"
            options.append((label, sid))
            
        select = self.query_one("#subscription-select", Select)
        select.set_options(options)
        
        if self._last_subscription_id:
             # Check if last used is in list
             if any(s[1] == self._last_subscription_id for s in options):
                 select.value = self._last_subscription_id
        
        select.prompt = "Select Subscription" if options else "No subscriptions found"
        
        if select.value:
            self._load_resource_groups(select.value)

    async def _load_resource_groups(self, subscription_id: str) -> None:
        """Load resource groups for selected subscription."""
        rgs = await self._cli.list_resource_groups(subscription_id)
        
        options = []
        for rg in rgs:
            name = rg.get('name', '')
            location = rg.get('location', '')
            label = f"{name} ({location})"
            options.append((label, name))
            
        # Add recent RGs if they aren't in the list (maybe deleted, but keep history?)
        # For now just use what's in Azure
            
        select = self.query_one("#rg-name-select", Select)
        select.set_options(options)
    
    def _toggle_rg_picker(self, show: bool) -> None:
        """Show or hide RG picker."""
        picker = self.query_one("#rg-name-select", Select)
        label = self.query_one("#rg-name-label", Label)
        
        if show:
            picker.remove_class("hidden")
            label.remove_class("hidden")
            if self.subscription_id:
                # Reload if we have context
                import asyncio
                asyncio.create_task(self._load_resource_groups(self.subscription_id))
        else:
            picker.add_class("hidden")
            label.add_class("hidden")
            self.rg_name = None
            # Prepare to clear selection
            if hasattr(picker, "clear"):
                picker.clear()
            else:
                 # Fallback for older versions if clear doesn't exist (though error suggested it)
                 try:
                     picker.value = None
                 except Exception:
                     pass
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "config-input":
            self.config_path = event.value.strip()
            self.check_config_path()
        elif event.input.id == "participant-input":
            self.participant = event.value.strip().lower()
            self.check_participant_slug()
        
        self._update_preview()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "ttl-select":
            self.ttl = str(event.value)
        elif event.select.id == "subscription-select":
            self.subscription_id = str(event.value) if event.value else None
            if self.subscription_id:
                import asyncio
                asyncio.create_task(self._load_resource_groups(self.subscription_id))
        elif event.select.id == "rg-name-select":
            self.rg_name = str(event.value) if event.value else None
            self.check_rg_selection()
            
        self._update_preview()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio set changes."""
        if event.radio_set.id == "rg-mode-radios":
            mode = str(event.pressed.value)
            self.rg_mode = mode
            self._toggle_rg_picker(mode == "existing")
            self.check_rg_selection()
            self._update_preview()
    
    
    def action_close(self) -> None:
        """Close this modal."""
        self.dismiss()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-btn":
            if self._is_form_valid():
                self.dismiss((
                    self.config_path,
                    self.participant,
                    self.ttl,
                    self.subscription_id,
                    self.rg_mode,
                    self.rg_name,
                    self.student_ids
                ))
        elif event.button.id == "cancel-btn":
            self.dismiss()
    
    def _validate_all(self) -> None:
        """Validate all fields."""
        self.check_config_path()
        self.check_participant_slug()
        self.check_rg_selection()
        
    def check_rg_selection(self) -> None:
        """Validate RG selection."""
        error_widget = self.query_one("#rg-error", Static)
        
        if self.rg_mode == "existing":
            if not self.rg_name:
                self.rg_valid = False
                error_widget.update("Must select a Resource Group")
            else:
                self.rg_valid = True
                error_widget.update("")
        else:
            self.rg_valid = True
            error_widget.update("")
    
    def check_config_path(self) -> None:
        """Validate config path."""
        error_widget = self.query_one("#config-error", Static)
        
        if not self.config_path:
            self.config_valid = False
            error_widget.update("")
            return
        
        if not self.config_path.startswith("/"):
            self.config_valid = False
            error_widget.update("Config path must be absolute")
            return
        
        import os
        if not os.path.isfile(self.config_path):
            self.config_valid = False
            error_widget.update("Config file not found")
            return
        
        self.config_valid = True
        error_widget.update("✓ Valid")
        error_widget.set_classes("success")
    
    def check_participant_slug(self) -> None:
        """Validate participant slug."""
        error_widget = self.query_one("#participant-error", Static)
        
        if not self.participant:
            self.participant_valid = False
            error_widget.update("")
            return
        
        pattern = re.compile(r'^[a-z0-9-]+$')
        if not pattern.match(self.participant):
            self.participant_valid = False
            error_widget.update("Must be lowercase alphanumeric with hyphens only")
            return
        
        self.participant_valid = True
        error_widget.update("✓ Valid")
        error_widget.set_classes("success")
    
    def _is_form_valid(self) -> bool:
        """Check if form is valid for submission."""
        return self.config_valid and self.participant_valid and self.ttl_valid and self.rg_valid
    
    def _update_preview(self) -> None:
        """Update the preview panel."""
        lab_id_preview = self.query_one("#preview-lab-id", Static)
        command_preview = self.query_one("#preview-command", Static)
        warning_text = self.query_one("#warning-text", Static)
        
        # Generate lab-id preview
        if self.participant:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
            lab_id_preview.update(f"Lab ID: azure-{self.participant}-{timestamp}-xxxx")
        else:
            lab_id_preview.update("Lab ID: (enter participant)")
        
        # Generate command preview
        if self.config_path and self.participant:
            cmd = f"./avd-lab.sh create --config {self.config_path} --participant {self.participant} --ttl {self.ttl}"
            
            if self.subscription_id:
                cmd += f" --subscription {self.subscription_id}"
                
            if self.rg_mode == "existing":
                 cmd += f" --rg-mode existing --rg-name {self.rg_name or '<missing>'}"
            
            command_preview.update(f"Command: {cmd}")
        else:
            command_preview.update("Command: (fill required fields)")
        
        # Show warnings
        warnings = []
        if not self.config_valid and self.config_path:
            warnings.append("• Invalid config path")
        if not self.participant_valid and self.participant:
            warnings.append("• Invalid participant slug")
        
        if warnings:
            warning_text.update("\n".join(warnings))
        else:
            warning_text.update("")
