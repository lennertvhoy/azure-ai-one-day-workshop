"""
AVD Lab TUI - CLI Runner Service

Safe subprocess wrapper for executing avd-lab.sh commands.
Uses explicit absolute paths and argument arrays (no shell string concatenation).
"""

import asyncio
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import StreamReader


class ExitCode(Enum):
    """Exit codes from avd-lab.sh"""
    SUCCESS = 0
    VALIDATION_ERROR = 1
    AZURE_ERROR = 2
    SAFETY_BLOCKED = 3


@dataclass
class CommandResult:
    """Result of a CLI command execution."""
    exit_code: int
    stdout: str
    stderr: str
    command: str
    success: bool = field(init=False)
    
    def __post_init__(self):
        self.success = self.exit_code == ExitCode.SUCCESS.value


@dataclass
class LabInfo:
    """Parsed lab information."""
    lab_id: str
    participant: str
    resource_group: str
    location: str
    expiry: str
    status: str = "unknown"
    host_pool: Optional[str] = None
    workspace: Optional[str] = None
    workspace_url: Optional[str] = None


class CliRunner:
    """
    Safe subprocess wrapper for avd-lab.sh commands.
    
    All commands use absolute paths and argument arrays.
    No shell string concatenation for user input.
    """
    
    # Absolute path to the backend script
    SCRIPT_PATH = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/avd-lab.sh"
    LOGS_DIR = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/logs/avd-lab"
    CONFIG_DIR = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/config"
    DEFAULT_CONFIG = "/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/config/lab-dev.json"
    
    # Validation patterns
    PARTICIPANT_PATTERN = re.compile(r'^[a-z0-9-]+$')
    TTL_PATTERN = re.compile(r'^[0-9]+[hd]$')
    
    def __init__(self):
        """Initialize the CLI runner."""
        self._validate_script_exists()
    
    def _validate_script_exists(self) -> None:
        """Ensure the backend script exists."""
        if not os.path.isfile(self.SCRIPT_PATH):
            raise FileNotFoundError(f"Backend script not found: {self.SCRIPT_PATH}")
        if not os.access(self.SCRIPT_PATH, os.X_OK):
            raise PermissionError(f"Backend script not executable: {self.SCRIPT_PATH}")
    
    def _build_command(self, command: str, *args: str) -> list[str]:
        """
        Build a command argument list.
        
        Uses explicit argument arrays - no shell concatenation.
        """
        cmd = [self.SCRIPT_PATH, command]
        cmd.extend(args)
        return cmd
    
    def _format_command_for_display(self, cmd: list[str]) -> str:
        """Format command for display (with proper quoting)."""
        return " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
    
    def validate_config_path(self, config_path: str) -> bool:
        """Validate that config path exists and is absolute."""
        if not os.path.isabs(config_path):
            return False
        return os.path.isfile(config_path)
    
    def validate_participant(self, participant: str) -> bool:
        """Validate participant slug format."""
        return bool(self.PARTICIPANT_PATTERN.match(participant))
    
    def validate_ttl(self, ttl: str) -> bool:
        """Validate TTL format."""
        return bool(self.TTL_PATTERN.match(ttl))
    
    async def run_command(
        self,
        command: str,
        *args: str,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run a command asynchronously.
        
        Args:
            command: The avd-lab.sh command (validate, create, destroy, status)
            *args: Additional arguments
            on_stdout: Optional callback for stdout lines
            on_stderr: Optional callback for stderr lines
            
        Returns:
            CommandResult with exit code and output
        """
        cmd = self._build_command(command, *args)
        command_str = self._format_command_for_display(cmd)
        
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,  # type: ignore[attr-defined]
                stderr=asyncio.subprocess.PIPE,  # type: ignore[attr-defined]
            )
            
            async def read_stream(
                stream: "asyncio.StreamReader",
                lines: list[str],
                callback: Optional[Callable[[str], None]]
            ):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace').rstrip('\n')
                    lines.append(decoded)
                    cb = callback
                    if cb is not None:
                        cb(decoded)
            
            # Read both streams concurrently
            # Note: process.stdout and process.stderr are guaranteed non-None when PIPE is used
            stdout_stream = process.stdout
            stderr_stream = process.stderr
            if stdout_stream is not None and stderr_stream is not None:
                await asyncio.gather(
                    read_stream(stdout_stream, stdout_lines, on_stdout),
                    read_stream(stderr_stream, stderr_lines, on_stderr),
                )
            
            exit_code = await process.wait()
            
        except Exception as e:
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                command=command_str,
            )
        
        return CommandResult(
            exit_code=exit_code,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            command=command_str,
        )

    async def list_subscriptions(self) -> list[dict[str, str]]:
        """
        List available Azure subscriptions.
        
        Returns:
            List of dicts with 'id', 'name', 'state', 'tenantId'
        """
        import json
        
        cmd = ["az", "account", "list", "--output", "json"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return json.loads(stdout.decode('utf-8'))
            else:
                return []
        except Exception:
            return []

    async def list_resource_groups(self, subscription_id: Optional[str] = None) -> list[dict[str, str]]:
        """
        List resource groups in a subscription.
        
        Args:
            subscription_id: Optional subscription ID to scope the list
            
        Returns:
            List of dicts with 'name', 'location', 'tags'
        """
        import json
        
        cmd = ["az", "group", "list", "--output", "json"]
        if subscription_id:
            cmd.extend(["--subscription", subscription_id])
            
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return json.loads(stdout.decode('utf-8'))
            else:
                return []
        except Exception:
            return []

    async def create_resource_group(self, name: str, location: str) -> bool:
        """Create a resource group."""
        cmd = ["az", "group", "create", "--name", name, "--location", location]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def delete_resource_group(self, name: str) -> bool:
        """Delete a resource group."""
        cmd = ["az", "group", "delete", "--name", name, "--yes", "--no-wait"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
    
    # === High-level command wrappers ===
    
    async def validate(
        self,
        config_path: str,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run validate command.
        
        Args:
            config_path: Absolute path to config file
            on_output: Optional callback for output lines
        """
        if not self.validate_config_path(config_path):
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr=f"Invalid config path: {config_path}",
                command="",
            )
        
        return await self.run_command(
            "validate",
            "--config", config_path,
            on_stdout=on_output,
            on_stderr=on_output,
        )
    
    async def create(
        self,
        config_path: str,
        participant: str,
        ttl: str = "8h",
        subscription_id: Optional[str] = None,
        rg_mode: str = "new_per_lab",
        rg_name: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run create command.
        
        Args:
            config_path: Absolute path to config file
            participant: Participant slug (validated)
            ttl: Time-to-live (e.g., '8h', '1d')
            subscription_id: Optional subscription ID
            rg_mode: Resource group mode ('new_per_lab' or 'existing')
            rg_name: Existing resource group name (required if rg_mode='existing')
            on_output: Optional callback for output lines
        """
        # Validate inputs
        if not self.validate_config_path(config_path):
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr=f"Invalid config path: {config_path}",
                command="",
            )
        
        if not self.validate_participant(participant):
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr=f"Invalid participant slug: {participant}. Must match {self.PARTICIPANT_PATTERN.pattern}",
                command="",
            )
        
        if not self.validate_ttl(ttl):
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr=f"Invalid TTL format: {ttl}. Use format like '8h' or '1d'",
                command="",
            )
        
        args = [
            "create",
            "--config", config_path,
            "--participant", participant,
            "--ttl", ttl,
        ]
        
        if subscription_id:
            args.extend(["--subscription", subscription_id])
            
        if rg_mode:
            args.extend(["--rg-mode", rg_mode])
            
        if rg_name:
            args.extend(["--rg-name", rg_name])
        
        return await self.run_command(
            *args,
            on_stdout=on_output,
            on_stderr=on_output,
        )
    
    async def destroy(
        self,
        lab_id: Optional[str] = None,
        participant: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run destroy command.
        
        Args:
            lab_id: Lab ID to destroy
            participant: Participant slug (alternative to lab_id)
            on_output: Optional callback for output lines
        """
        args = ["destroy", "--yes"]
        
        if lab_id:
            args.extend(["--lab-id", lab_id])
        elif participant:
            if not self.validate_participant(participant):
                return CommandResult(
                    exit_code=ExitCode.VALIDATION_ERROR.value,
                    stdout="",
                    stderr=f"Invalid participant slug: {participant}",
                    command="",
                )
            args.extend(["--participant", participant])
        else:
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr="Either lab_id or participant is required",
                command="",
            )
        
        return await self.run_command(
            *args,
            on_stdout=on_output,
            on_stderr=on_output,
        )
    
    async def status(
        self,
        lab_id: Optional[str] = None,
        participant: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run status command.
        
        Args:
            lab_id: Lab ID to check
            participant: Participant slug (alternative to lab_id)
            on_output: Optional callback for output lines
        """
        args = ["status"]
        
        if lab_id:
            args.extend(["--lab-id", lab_id])
        elif participant:
            if not self.validate_participant(participant):
                return CommandResult(
                    exit_code=ExitCode.VALIDATION_ERROR.value,
                    stdout="",
                    stderr=f"Invalid participant slug: {participant}",
                    command="",
                )
            args.extend(["--participant", participant])
        else:
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr="Either lab_id or participant is required",
                command="",
            )
        
        return await self.run_command(
            *args,
            on_stdout=on_output,
            on_stderr=on_output,
        )
    
    async def estimate_cost(
        self,
        config_path: str,
        hours: int = 8,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run estimate-cost command.
        
        Args:
            config_path: Absolute path to config file
            hours: Number of hours for estimation
            on_output: Optional callback for output lines
        """
        if not self.validate_config_path(config_path):
            return CommandResult(
                exit_code=ExitCode.VALIDATION_ERROR.value,
                stdout="",
                stderr=f"Invalid config path: {config_path}",
                command="",
            )
        
        return await self.run_command(
            "estimate-cost",
            "--config", config_path,
            "--hours", str(hours),
            on_stdout=on_output,
            on_stderr=on_output,
        )
    
    def get_log_files(self) -> list[str]:
        """Get list of log files in the logs directory."""
        logs_dir = Path(self.LOGS_DIR)
        if not logs_dir.exists():
            return []
        
        log_files = sorted(
            logs_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [str(f) for f in log_files]
    
    def read_log_file(self, log_path: str) -> str:
        """Read a log file's contents."""
        path = Path(log_path)
        if not path.exists():
            return f"Log file not found: {log_path}"
        return path.read_text(encoding='utf-8', errors='replace')
