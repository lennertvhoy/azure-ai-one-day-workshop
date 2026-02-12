"""
AVD Lab TUI - State Management Service

Manages local UI state (recent participants, config paths, etc.)
Does not store secrets.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Job:
    """Represents a background operation."""
    id: str
    type: str  # create, destroy, validate, refresh
    target: str  # lab_id or participant
    status: str = "queued"  # queued, running, succeeded, failed, cancelled
    start_time: Optional[str] = None
    duration: Optional[str] = None
    last_log: str = ""
    errors: list[str] = field(default_factory=list)

@dataclass
class UIState:
    """UI state data model."""
    recent_participants: list[str] = field(default_factory=list)
    last_config_path: Optional[str] = None
    last_ttl: str = "8h"
    recently_selected_lab_ids: list[str] = field(default_factory=list)
    last_refresh_time: Optional[str] = None
    
    last_subscription_id: Optional[str] = None
    last_rg_mode: str = "new_per_lab"
    recent_rg_names: list[str] = field(default_factory=list)
    
    # Active/Recent jobs (not persisted normally, but we keep in session)
    jobs: list[Job] = field(default_factory=list)

    # Limits
    MAX_RECENT_PARTICIPANTS = 10
    MAX_RECENT_LAB_IDS = 20
    MAX_RECENT_RG_NAMES = 10
    MAX_JOBS = 50


class StateManager:
    """
    Manages persistent UI state.
    
    State is stored in:
    /home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/tui/.state/ui-state.json
    
    Does not store secrets.
    """
    
    STATE_DIR = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/tui/.state"
    STATE_FILE = "ui-state.json"
    
    def __init__(self):
        """Initialize state manager and load existing state."""
        self._state = UIState()
        self._ensure_state_dir()
        self._load_state()
    
    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        Path(self.STATE_DIR).mkdir(parents=True, exist_ok=True)
    
    def _get_state_path(self) -> Path:
        """Get full path to state file."""
        return Path(self.STATE_DIR) / self.STATE_FILE
    
    def _load_state(self) -> None:
        """Load state from file if it exists."""
        state_path = self._get_state_path()
        
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._state = UIState(
                    recent_participants=data.get('recent_participants', []),
                    last_config_path=data.get('last_config_path'),
                    last_ttl=data.get('last_ttl', '8h'),
                    recently_selected_lab_ids=data.get('recently_selected_lab_ids', []),
                    last_refresh_time=data.get('last_refresh_time'),
                    last_subscription_id=data.get('last_subscription_id'),
                    last_rg_mode=data.get('last_rg_mode', 'new_per_lab'),
                    recent_rg_names=data.get('recent_rg_names', []),
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                # If state file is corrupted, start fresh
                self._state = UIState()
    
    def _save_state(self) -> None:
        """Save state to file."""
        state_path = self._get_state_path()
        
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self._state), f, indent=2)
    
    @property
    def state(self) -> UIState:
        """Get current state."""
        return self._state
    
    # === Participant management ===
    
    def add_recent_participant(self, participant: str) -> None:
        """Add a participant to recent list."""
        if participant in self._state.recent_participants:
            self._state.recent_participants.remove(participant)
        
        self._state.recent_participants.insert(0, participant)
        
        # Trim to max size
        while len(self._state.recent_participants) > UIState.MAX_RECENT_PARTICIPANTS:
            self._state.recent_participants.pop()
        
        self._save_state()
    
    def get_recent_participants(self) -> list[str]:
        """Get list of recent participants."""
        return self._state.recent_participants.copy()
    
    # === Config path management ===
    
    def set_last_config_path(self, config_path: str) -> None:
        """Set the last used config path."""
        self._state.last_config_path = config_path
        self._save_state()
    
    def get_last_config_path(self) -> Optional[str]:
        """Get the last used config path."""
        return self._state.last_config_path
    
    # === TTL management ===
    
    def set_last_ttl(self, ttl: str) -> None:
        """Set the last used TTL."""
        self._state.last_ttl = ttl
        self._save_state()
    
    def get_last_ttl(self) -> str:
        """Get the last used TTL."""
        return self._state.last_ttl
    
    # === Lab ID management ===
    
    def add_recent_lab_id(self, lab_id: str) -> None:
        """Add a lab ID to recent list."""
        if lab_id in self._state.recently_selected_lab_ids:
            self._state.recently_selected_lab_ids.remove(lab_id)
        
        self._state.recently_selected_lab_ids.insert(0, lab_id)
        
        # Trim to max size
        while len(self._state.recently_selected_lab_ids) > UIState.MAX_RECENT_LAB_IDS:
            self._state.recently_selected_lab_ids.pop()
        
        self._save_state()
    
    def get_recent_lab_ids(self) -> list[str]:
        """Get list of recent lab IDs."""
        return self._state.recently_selected_lab_ids.copy()
    
    # === Refresh time management ===
    
    def update_refresh_time(self) -> None:
        """Update the last refresh time to now."""
        from datetime import datetime, timezone
        self._state.last_refresh_time = datetime.now(timezone.utc).isoformat()
        self._save_state()
    
    def get_last_refresh_time(self) -> Optional[str]:
        """Get the last refresh time."""
        return self._state.last_refresh_time
    
    # === Subscription management ===
    
    def set_last_subscription_id(self, subscription_id: Optional[str]) -> None:
        """Set the last used subscription ID."""
        self._state.last_subscription_id = subscription_id
        self._save_state()
    
    def get_last_subscription_id(self) -> Optional[str]:
        """Get the last used subscription ID."""
        return self._state.last_subscription_id
    
    # === RG management ===
    
    def set_last_rg_mode(self, mode: str) -> None:
        """Set the last used RG mode."""
        self._state.last_rg_mode = mode
        self._save_state()
    
    def get_last_rg_mode(self) -> str:
        """Get the last used RG mode."""
        return self._state.last_rg_mode
    
    def add_recent_rg_name(self, rg_name: str) -> None:
        """Add an RG name to recent list."""
        if rg_name in self._state.recent_rg_names:
            self._state.recent_rg_names.remove(rg_name)
        
        self._state.recent_rg_names.insert(0, rg_name)
        
        # Trim to max size
        while len(self._state.recent_rg_names) > UIState.MAX_RECENT_RG_NAMES:
            self._state.recent_rg_names.pop()
        
        self._save_state()
    
    def get_recent_rg_names(self) -> list[str]:
        """Get list of recent RG names."""
        return self._state.recent_rg_names.copy()

    # === Job management ===

    def add_job(self, job: Job) -> None:
        """Add a job to the session."""
        self._state.jobs.insert(0, job)
        if len(self._state.jobs) > UIState.MAX_JOBS:
            self._state.jobs.pop()
        # We don't persist jobs to disk normally
    
    def update_job(self, job_id: str, **kwargs) -> Optional[Job]:
        """Update a job's attributes."""
        for job in self._state.jobs:
            if job.id == job_id:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                return job
        return None

    def get_jobs(self) -> list[Job]:
        """Get all jobs."""
        return self._state.jobs

    # === Reset ===
    
    def reset_state(self) -> None:
        """Reset all state to defaults."""
        self._state = UIState()
        self._save_state()
