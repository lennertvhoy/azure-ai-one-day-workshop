"""
AVD Lab TUI - Student Manager

UI for managing students and sending guest invitations.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Input, Static
from textual.message import Message

from services.cli_runner import CliRunner
from services.student_service import StudentService, Student

class StudentManager(ModalScreen):
    """
    Modal screen to manage students and send invitations.
    """
    
    DEFAULT_CSS = """
    StudentManager {
        align: center middle;
    }
    
    StudentManager > Container {
        width: 100;
        height: 85%;
        background: #1e1e2e;
        border: thick #313244;
        padding: 1 2;
    }
    
    StudentManager .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        background: #89b4fa;
        color: #1e1e2e;
        padding: 1;
    }
    
    StudentManager .input-row {
        height: 3;
        margin-bottom: 1;
    }
    
    StudentManager Input {
        width: 1fr;
        margin-right: 1;
    }
    
    StudentManager DataTable {
        height: 1fr;
        margin-bottom: 1;
    }
    
    StudentManager .buttons {
        height: 3;
        align: center middle;
    }
    
    StudentManager Button {
        margin: 0 1;
    }
    
    StudentManager #status-msg {
        height: 1;
        margin-bottom: 1;
        color: #fab387;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]
    
    def __init__(self, cli_runner: CliRunner, student_service: StudentService, **kwargs):
        super().__init__(**kwargs)
        self._cli = cli_runner
        self._students = student_service
        
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Student Manager", classes="title")
            
            with Horizontal(classes="input-row"):
                yield Input(placeholder="student@example.com", id="student-email")
                yield Button("Invite Student", id="invite-btn", variant="primary")
            
            yield Label("", id="status-msg")
            
            yield DataTable(
                id="student-table", 
                cursor_type="row", 
                zebra_stripes=True
            )
            
            with Horizontal(classes="buttons"):
                yield Button("Remove Selected", id="remove-btn", variant="error")
                yield Button("Done (Esc)", id="close-btn")
                
    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Email", "Object ID", "Invited At")
        self._refresh_table()
        
    def _refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for student in self._students.get_students():
            table.add_row(student.email, student.object_id, student.invited_at)
            
    def action_close(self) -> None:
        self.dismiss()
        
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "invite-btn":
            await self._on_invite()
        elif event.button.id == "remove-btn":
            self._on_remove()
            
    async def _on_invite(self) -> None:
        email_input = self.query_one("#student-email", Input)
        email = email_input.value.strip()
        
        if not email or "@" not in email:
            self.query_one("#status-msg", Label).update("Invalid email address")
            return
            
        self.query_one("#status-msg", Label).update(f"Inviting {email}...")
        email_input.disabled = True
        self.query_one("#invite-btn", Button).disabled = True
        
        try:
            # We use CliRunner to invite
            import json
            result = await self._cli.invite_student(email)
            if result.success:
                # Parse Object ID
                import json
                
                # Robust JSON extraction to handle mixed logs/output
                candidates = []
                text = result.stdout.strip()
                idx = 0
                while idx < len(text):
                    start_idx = text.find('{', idx)
                    if start_idx == -1:
                        break
                    try:
                        obj, end_idx = json.JSONDecoder().raw_decode(text[start_idx:])
                        candidates.append(obj)
                        idx = start_idx + end_idx
                    except json.JSONDecodeError:
                        idx = start_idx + 1
                
                data = None
                # Iterate candidates (reversed) to find the one with expected keys
                for cand in reversed(candidates):
                    if "invitedUser" in cand or "id" in cand:
                        data = cand
                        break
                
                if not data and candidates:
                    data = candidates[-1]

                if data:
                    object_id = data.get("invitedUser", {}).get("id") or data.get("id")
                    if object_id:
                        self._students.add_student(email, object_id)
                        self._refresh_table()
                        self.query_one("#status-msg", Label).update(f"Successfully invited {email}")
                        self.query_one("#student-email", Input).value = ""
                    else:
                        self.query_one("#status-msg", Label).update("Failed to Parse Object ID from invitation")
                else:
                     self.query_one("#status-msg", Label).update("Invitation sent, but failed to parse response JSON")
            else:
                self.query_one("#status-msg", Label).update(f"Invitation failed: {result.stderr}")
        finally:
            email_input.disabled = False
            self.query_one("#invite-btn", Button).disabled = False

    def _on_remove(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            # Table rows correspond to our student list in order
            students = self._students.get_students()
            if table.cursor_row < len(students):
                student = students[table.cursor_row]
                self._students.remove_student(student.email)
                self._refresh_table()
                self.query_one("#status-msg", Label).update(f"Removed {student.email}")
