"""
AVD Lab TUI - Output Parser Service

Parses deterministic output lines from avd-lab.sh script.
Falls back to raw output if parsing fails.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ValidationResult:
    """Parsed validation result."""
    azure_cli: bool = False
    logged_in: bool = False
    user_name: Optional[str] = None
    subscription_id: Optional[str] = None
    subscription_name: Optional[str] = None
    providers: dict[str, bool] = field(default_factory=dict)
    bicep_version: Optional[str] = None
    quota_available: bool = False
    quota_details: Optional[str] = None
    network_ok: bool = False
    network_details: Optional[str] = None
    success: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CreateResult:
    """Parsed create command result."""
    lab_id: Optional[str] = None
    participant: Optional[str] = None
    resource_group: Optional[str] = None
    host_pool: Optional[str] = None
    workspace: Optional[str] = None
    workspace_url: Optional[str] = None
    expiry: Optional[str] = None
    estimated_cost: Optional[str] = None
    destroy_command: Optional[str] = None
    success: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class StatusResult:
    """Parsed status command result."""
    lab_id: Optional[str] = None
    resource_group: Optional[str] = None
    location: Optional[str] = None
    participant: Optional[str] = None
    expiry: Optional[str] = None
    time_remaining: Optional[str] = None
    expired: bool = False
    host_pools: list[dict] = field(default_factory=list)
    session_hosts: list[dict] = field(default_factory=list)
    vms: list[dict] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    success: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class DestroyResult:
    """Parsed destroy command result."""
    lab_id: Optional[str] = None
    resource_group: Optional[str] = None
    resources_deleted: list[str] = field(default_factory=list)
    orphaned_resources: list[str] = field(default_factory=list)
    success: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class CostEstimate:
    """Parsed cost estimate result."""
    vm_size: Optional[str] = None
    vm_count: Optional[int] = None
    hours: Optional[int] = None
    total_cost: Optional[str] = None
    success: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class LabListItem:
    """Lab info for dashboard listing."""
    lab_id: str
    participant: str
    resource_group: str
    location: str
    expiry: str
    status: str = "unknown"


class OutputParser:
    """
    Parser for avd-lab.sh output.
    
    Parses deterministic lines from script output.
    Falls back to raw output if parser fails.
    """
    
    # Patterns for parsing
    PATTERNS = {
        # Create output
        'lab_id': re.compile(r'^Lab ID:\s*(.+)$', re.MULTILINE),
        'participant': re.compile(r'^Participant:\s*(.+)$', re.MULTILINE),
        'resource_group': re.compile(r'^Resource Group:\s*(.+)$', re.MULTILINE),
        'host_pool': re.compile(r'^Host Pool:\s*(.+)$', re.MULTILINE),
        'workspace': re.compile(r'^Workspace:\s*(.+)$', re.MULTILINE),
        'workspace_url': re.compile(r'^Workspace URL:\s*(.+)$', re.MULTILINE),
        'expiry': re.compile(r'^Expiry:\s*(.+)$', re.MULTILINE),
        'estimated_cost': re.compile(r'Estimated cost for TTL period:\s*\$([0-9.]+)', re.MULTILINE),
        'destroy_cmd': re.compile(r'\./avd-lab\.sh destroy --lab-id\s+(\S+)\s+--yes'),
        
        # Status output
        'location': re.compile(r'^Location:\s*(.+)$', re.MULTILINE),
        'time_remaining': re.compile(r'Time remaining:\s*(.+)$', re.MULTILINE),
        'expired': re.compile(r'Lab has expired'),
        
        # Validation output
        'logged_in_as': re.compile(r'Logged in as:\s*(.+)$', re.MULTILINE),
        'subscription': re.compile(r'Subscription:\s*(\S+)\s*\((.+)\)$', re.MULTILINE),
        'provider_registered': re.compile(r'Provider registered:\s*(.+)$', re.MULTILINE),
        'bicep_available': re.compile(r'Bicep available:\s*(.+)$', re.MULTILINE),
        'quota_available': re.compile(r'Quota available:\s*(\d+)\s*VMs of type\s+(\S+)'),
        'no_network_collision': re.compile(r'No network collisions detected'),
        
        # Cost estimate
        'vm_size': re.compile(r'^VM Size:\s*(.+)$', re.MULTILINE),
        'num_vms': re.compile(r'^Number of VMs:\s*(\d+)$', re.MULTILINE),
        'duration': re.compile(r'^Duration:\s*(\d+)\s*hours$', re.MULTILINE),
        'total_cost': re.compile(r'Estimated Total Cost:\s*\$([0-9.]+)\s*USD'),
        
        # Error patterns
        'error': re.compile(r'\[ERROR\]\s*(.+)$', re.MULTILINE),
        'warning': re.compile(r'\[WARN\]\s*(.+)$', re.MULTILINE),
        'success_marker': re.compile(r'✓'),
    }
    
    def parse_validation(self, output: str) -> ValidationResult:
        """Parse validate command output."""
        result = ValidationResult()
        
        # Check for Azure CLI
        if 'Azure CLI found' in output or 'Azure CLI' in output:
            result.azure_cli = True
        
        # Check for logged in user
        match = self.PATTERNS['logged_in_as'].search(output)
        if match:
            result.logged_in = True
            result.user_name = match.group(1).strip()
        
        # Check for subscription
        match = self.PATTERNS['subscription'].search(output)
        if match:
            result.subscription_id = match.group(1).strip()
            result.subscription_name = match.group(2).strip()
        
        # Check for providers
        for match in self.PATTERNS['provider_registered'].finditer(output):
            provider = match.group(1).strip()
            result.providers[provider] = True
        
        # Check for Bicep
        match = self.PATTERNS['bicep_available'].search(output)
        if match:
            result.bicep_version = match.group(1).strip()
        
        # Check for quota
        match = self.PATTERNS['quota_available'].search(output)
        if match:
            result.quota_available = True
            result.quota_details = f"{match.group(1)} VMs of {match.group(2)}"
        
        # Check for network
        if self.PATTERNS['no_network_collision'].search(output):
            result.network_ok = True
        
        # Check for errors
        for match in self.PATTERNS['error'].finditer(output):
            result.errors.append(match.group(1).strip())
        
        # Check for warnings
        for match in self.PATTERNS['warning'].finditer(output):
            result.warnings.append(match.group(1).strip())
        
        # Check for success
        if 'All prerequisites validated' in output or 'Validation completed successfully' in output:
            result.success = True
        
        return result
    
    def parse_create(self, output: str) -> CreateResult:
        """Parse create command output."""
        result = CreateResult()
        
        # Extract fields
        match = self.PATTERNS['lab_id'].search(output)
        if match:
            result.lab_id = match.group(1).strip()
        
        match = self.PATTERNS['participant'].search(output)
        if match:
            result.participant = match.group(1).strip()
        
        match = self.PATTERNS['resource_group'].search(output)
        if match:
            result.resource_group = match.group(1).strip()
        
        match = self.PATTERNS['host_pool'].search(output)
        if match:
            result.host_pool = match.group(1).strip()
        
        match = self.PATTERNS['workspace'].search(output)
        if match:
            result.workspace = match.group(1).strip()
        
        match = self.PATTERNS['workspace_url'].search(output)
        if match:
            result.workspace_url = match.group(1).strip()
        
        match = self.PATTERNS['expiry'].search(output)
        if match:
            result.expiry = match.group(1).strip()
        
        match = self.PATTERNS['estimated_cost'].search(output)
        if match:
            result.estimated_cost = f"${match.group(1)}"
        
        match = self.PATTERNS['destroy_cmd'].search(output)
        if match:
            result.destroy_command = f"./avd-lab.sh destroy --lab-id {match.group(1)} --yes"
        
        # Check for errors
        for match in self.PATTERNS['error'].finditer(output):
            result.errors.append(match.group(1).strip())
        
        # Check for success
        if 'AVD Lab created successfully' in output:
            result.success = True
        
        return result
    
    def parse_status(self, output: str) -> StatusResult:
        """Parse status command output."""
        result = StatusResult()
        
        # Extract fields
        match = self.PATTERNS['lab_id'].search(output)
        if match:
            result.lab_id = match.group(1).strip()
        
        match = self.PATTERNS['resource_group'].search(output)
        if match:
            result.resource_group = match.group(1).strip()
        
        match = self.PATTERNS['location'].search(output)
        if match:
            result.location = match.group(1).strip()
        
        match = self.PATTERNS['expiry'].search(output)
        if match:
            result.expiry = match.group(1).strip()
        
        match = self.PATTERNS['time_remaining'].search(output)
        if match:
            result.time_remaining = match.group(1).strip()
        
        # Check for expired
        if self.PATTERNS['expired'].search(output):
            result.expired = True
        
        # Parse tags (look for "Tags:" section)
        tags_section = re.search(r'Tags:\n((?:  .+\n?)+)', output)
        if tags_section:
            for line in tags_section.group(1).strip().split('\n'):
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    result.tags[key.strip()] = value.strip()
        
        # Extract participant from tags
        if 'participant' in result.tags:
            result.participant = result.tags['participant']
        
        # Parse host pools
        hp_section = re.search(r'Host Pools:\n((?:  .+\n?)+)', output)
        if hp_section:
            current_hp = {}
            for line in hp_section.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('Name:'):
                    if current_hp:
                        result.host_pools.append(current_hp)
                    current_hp = {'name': line.split(':', 1)[1].strip()}
                elif line.startswith('Type:'):
                    current_hp['type'] = line.split(':', 1)[1].strip()
                elif line.startswith('Max Sessions:'):
                    current_hp['max_sessions'] = line.split(':', 1)[1].strip()
            if current_hp:
                result.host_pools.append(current_hp)
        
        # Parse session hosts
        sh_section = re.search(r'Session Hosts:\n((?:  .+\n?)+)', output)
        if sh_section:
            for line in sh_section.group(1).strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    name, status = line.rsplit(':', 1)
                    result.session_hosts.append({
                        'name': name.strip(),
                        'status': status.strip()
                    })
        
        # Parse VMs
        vm_section = re.search(r'Virtual Machines:\n((?:  .+\n?)+)', output)
        if vm_section:
            for line in vm_section.group(1).strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    name, status = line.rsplit(':', 1)
                    result.vms.append({
                        'name': name.strip(),
                        'status': status.strip()
                    })
        
        # Check for errors
        for match in self.PATTERNS['error'].finditer(output):
            result.errors.append(match.group(1).strip())
        
        # Check for success (found lab info)
        if result.lab_id or result.resource_group:
            result.success = True
        
        return result
    
    def parse_destroy(self, output: str) -> DestroyResult:
        """Parse destroy command output."""
        result = DestroyResult()
        
        # Extract lab-id
        match = self.PATTERNS['lab_id'].search(output)
        if match:
            result.lab_id = match.group(1).strip()
        
        # Extract resource group
        match = self.PATTERNS['resource_group'].search(output)
        if match:
            result.resource_group = match.group(1).strip()
        
        # Parse resources to be deleted
        resources_section = re.search(r'Resources to be deleted:\n((?:  .+\n?)+)', output)
        if resources_section:
            for line in resources_section.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    # Remove the "- " prefix
                    resource_name = line.removeprefix('- ').strip()
                    result.resources_deleted.append(resource_name)
        
        # Parse orphaned resources
        orphaned_section = re.search(r'Found \d+ orphaned resources:\n((?:  .+\n?)+)', output)
        if orphaned_section:
            for line in orphaned_section.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    # Remove the "- " prefix
                    resource_name = line.removeprefix('- ').strip()
                    result.orphaned_resources.append(resource_name)
        
        # Check for errors
        for match in self.PATTERNS['error'].finditer(output):
            result.errors.append(match.group(1).strip())
        
        # Check for success
        if 'AVD Lab destroyed successfully' in output:
            result.success = True
        
        return result
    
    def parse_cost_estimate(self, output: str) -> CostEstimate:
        """Parse cost estimate output."""
        result = CostEstimate()
        
        match = self.PATTERNS['vm_size'].search(output)
        if match:
            result.vm_size = match.group(1).strip()
        
        match = self.PATTERNS['num_vms'].search(output)
        if match:
            result.vm_count = int(match.group(1))
        
        match = self.PATTERNS['duration'].search(output)
        if match:
            result.hours = int(match.group(1))
        
        match = self.PATTERNS['total_cost'].search(output)
        if match:
            result.total_cost = f"${match.group(1)} USD"
        
        # Check for errors
        for match in self.PATTERNS['error'].finditer(output):
            result.errors.append(match.group(1).strip())
        
        if result.total_cost:
            result.success = True
        
        return result
    
    def parse_log_line(self, line: str) -> Optional[dict]:
        """Parse a JSON log line."""
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
    
    def extract_lab_list(self, output: str) -> list[LabListItem]:
        """
        Extract list of labs from Azure resource query output.
        This is used when listing all labs for the dashboard.
        """
        labs = []
        
        # Try to parse as JSON (from az resource list)
        try:
            # Look for JSON array in output
            json_match = re.search(r'\[.*\]', output, re.DOTALL)
            if json_match:
                resources = json.loads(json_match.group())
                
                # Group by lab-id
                lab_groups: dict[str, dict] = {}
                for resource in resources:
                    tags = resource.get('tags', {})
                    lab_id = tags.get('lab-id')
                    if lab_id and tags.get('managed-by') == 'avd-lab-tool':
                        if lab_id not in lab_groups:
                            lab_groups[lab_id] = {
                                'lab_id': lab_id,
                                'participant': tags.get('participant', 'unknown'),
                                'resource_group': resource.get('resourceGroup', 'unknown'),
                                'location': resource.get('location', 'unknown'),
                                'expiry': tags.get('expiry', 'unknown'),
                            }
                
                for lab_data in lab_groups.values():
                    labs.append(LabListItem(
                        lab_id=lab_data['lab_id'],
                        participant=lab_data['participant'],
                        resource_group=lab_data['resource_group'],
                        location=lab_data['location'],
                        expiry=lab_data['expiry'],
                        status=self._determine_status(lab_data['expiry']),
                    ))
        except (json.JSONDecodeError, KeyError):
            pass
        
        return labs
    
    def _determine_status(self, expiry: str) -> str:
        """Determine lab status from expiry time."""
        if expiry == 'unknown':
            return 'unknown'
        
        try:
            # Parse ISO 8601 expiry time
            if expiry.endswith('Z'):
                expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            else:
                expiry_dt = datetime.fromisoformat(expiry)
            
            # Compare with current time
            now = datetime.now(expiry_dt.tzinfo) if expiry_dt.tzinfo else datetime.utcnow()
            
            if expiry_dt < now:
                return 'expired'
            else:
                return 'running'
        except (ValueError, TypeError):
            return 'unknown'
