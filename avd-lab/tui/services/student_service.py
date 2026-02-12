"""
AVD Lab TUI - Student Service

Manages a local registry of students and interfaces with the CLI for guest invitations.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path

@dataclass
class Student:
    email: str
    object_id: str
    invited_at: str

class StudentService:
    def __init__(self, state_dir: str = ".state"):
        self.state_dir = Path(state_dir)
        self.storage_path = self.state_dir / "students.json"
        self._ensure_storage()
        self.students: List[Student] = []
        self.load_students()

    def _ensure_storage(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            with open(self.storage_path, "w") as f:
                json.dump([], f)

    def load_students(self):
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.students = [Student(**s) for s in data]
        except (json.JSONDecodeError, FileNotFoundError):
            self.students = []

    def save_students(self):
        with open(self.storage_path, "w") as f:
            json.dump([asdict(s) for s in self.students], f, indent=4)

    def add_student(self, email: str, object_id: str):
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Avoid duplicates
        self.students = [s for s in self.students if s.email != email]
        self.students.append(Student(email=email, object_id=object_id, invited_at=now))
        self.save_students()

    def remove_student(self, email: str):
        self.students = [s for s in self.students if s.email != email]
        self.save_students()

    def get_students(self) -> List[Student]:
        return self.students

    def get_object_id_by_email(self, email: str) -> Optional[str]:
        for s in self.students:
            if s.email == email:
                return s.object_id
        return None
