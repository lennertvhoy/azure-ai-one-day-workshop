"""
Tests for student identity onboarding flow.

This module tests:
1. Existing member user lookup
2. Existing guest user lookup
3. New invite success
4. Invite returns no ID then lookup succeeds
5. Permission denied error
6. User unresolved timeout
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.parser import OutputParser, StudentInviteResult
from services.cli_runner import CliRunner, ExitCode


@pytest.fixture
def parser():
    return OutputParser()


@pytest.fixture
def runner():
    with patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True):
        yield CliRunner()


# === Parser Tests ===

class TestStudentInviteParser:
    """Tests for parsing student invite JSON output."""

    def test_parse_existing_member_user(self, parser):
        """Test parsing existing member user response."""
        output = """[INFO] Processing student: student1@university.edu
[INFO] Looking up existing user: student1@university.edu
[INFO] Found existing user: student1@university.edu (Object ID: 12345-abcde, Type: member)
[INFO] User student1@university.edu is an existing user
{"email":"student1@university.edu","objectId":"12345-abcde","userType":"member","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "student1@university.edu"
        assert result.object_id == "12345-abcde"
        assert result.user_type == "member"
        assert result.provisioning_action == "existing_user"
        assert result.status == "success"
        assert result.error_code is None
        assert result.error_message is None

    def test_parse_existing_guest_user(self, parser):
        """Test parsing existing guest user response."""
        output = """[INFO] Processing student: guest1@external.com
[INFO] Looking up existing user: guest1@external.com
[INFO] Found existing user: guest1@external.com (Object ID: 67890-fghij, Type: guest)
[INFO] User guest1@external.com is an existing user
{"email":"guest1@external.com","objectId":"67890-fghij","userType":"guest","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "guest1@external.com"
        assert result.object_id == "67890-fghij"
        assert result.user_type == "guest"
        assert result.provisioning_action == "existing_user"
        assert result.status == "success"

    def test_parse_new_invite_success(self, parser):
        """Test parsing new guest invitation success response."""
        output = """[INFO] Processing student: newstudent@university.edu
[INFO] Looking up existing user: newstudent@university.edu
[INFO] User not found. Inviting new user: newstudent@university.edu
[INFO] Invited student newstudent@university.edu (Object ID: new-12345-uuid)
[SUCCESS] Invited student newstudent@university.edu (Object ID: new-12345-uuid)
{"email":"newstudent@university.edu","objectId":"new-12345-uuid","userType":"guest","provisioningAction":"invited","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "newstudent@university.edu"
        assert result.object_id == "new-12345-uuid"
        assert result.user_type == "guest"
        assert result.provisioning_action == "invited"
        assert result.status == "success"
        assert result.error_code is None

    def test_parse_invite_no_id_then_lookup_succeeds(self, parser):
        """Test parsing invite that returns no ID initially but lookup succeeds."""
        output = """[INFO] Processing student: delayeduser@external.com
[INFO] Looking up existing user: delayeduser@external.com
[INFO] User not found. Inviting new user: delayeduser@external.com
[INFO] Object ID not in invite response, resolving via lookup...
[INFO] Retry 1/5: looking up delayeduser@external.com
[INFO] Retry 2/5: looking up delayeduser@external.com
[INFO] Found user via lookup: delayeduser@external.com
[SUCCESS] Invited student delayeduser@external.com
{"email":"delayeduser@external.com","objectId":"resolved-67890","userType":"guest","provisioningAction":"invited","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "delayeduser@external.com"
        assert result.object_id == "resolved-67890"
        assert result.user_type == "guest"
        assert result.provisioning_action == "invited"

    def test_parse_permission_denied_error(self, parser):
        """Test parsing permission denied error response."""
        output = """[INFO] Processing student: unauthorized@test.com
[INFO] Looking up existing user: unauthorized@test.com
[ERROR] Failed to invite student: Insufficient privileges to complete the operation.
{"email":"unauthorized@test.com","objectId":"","userType":"","provisioningAction":"invite_failed","status":"error","errorCode":"403","errorMessage":"Insufficient privileges to complete the operation."}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is False
        assert result.email == "unauthorized@test.com"
        assert result.object_id is None
        assert result.user_type is None
        assert result.provisioning_action == "invite_failed"
        assert result.status == "error"
        assert result.error_code == "403"
        assert "Insufficient privileges" in result.error_message

    def test_parse_user_unresolved_timeout(self, parser):
        """Test parsing user unresolved timeout error."""
        output = """[INFO] Processing student: timeout@test.com
[INFO] Looking up existing user: timeout@test.com
[INFO] User not found. Inviting new user: timeout@test.com
[INFO] Object ID not in invite response, resolving via lookup...
[INFO] Retry 1/5: looking up timeout@test.com
[INFO] Retry 2/5: looking up timeout@test.com
[INFO] Retry 3/5: looking up timeout@test.com
[INFO] Retry 4/5: looking up timeout@test.com
[INFO] Retry 5/5: looking up timeout@test.com
[ERROR] Failed to resolve Object ID after invitation
{"email":"timeout@test.com","objectId":"","userType":"","provisioningAction":"invite_failed","status":"error","errorCode":"1","errorMessage":"Failed to resolve Object ID after invitation"}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is False
        assert result.email == "timeout@test.com"
        assert result.object_id is None
        assert result.provisioning_action == "invite_failed"
        assert result.status == "error"
        assert result.error_code == "1"
        assert "Failed to resolve Object ID" in result.error_message

    def test_parse_empty_output(self, parser):
        """Test parsing empty output returns default result."""
        result = parser.parse_student_invite("")
        
        assert result.success is False
        assert result.email == ""
        assert result.object_id is None

    def test_parse_invalid_json(self, parser):
        """Test parsing invalid JSON returns default result."""
        output = """[INFO] Some log output
not json at all
more text"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is False
        assert result.email == ""


# === CLI Runner Tests ===

class TestStudentInviteCliRunner:
    """Tests for CLI runner student invite functionality."""

    @pytest.mark.asyncio
    async def test_invite_student_calls_correct_command(self, runner):
        """Test that invite_student calls the shell script with correct arguments."""
        with patch.object(runner, 'run_command', new_callable=AsyncMock) as mock_run:
            mock_run.return_value.exit_code = 0
            mock_run.return_value.stdout = '{"email":"test@test.com","objectId":"123","userType":"member","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}'
            
            result = await runner.invite_student("test@test.com")
            
            args = mock_run.call_args[0]
            assert "invite-student" in args
            assert "--email" in args
            assert "test@test.com" in args

    @pytest.mark.asyncio
    async def test_invite_student_returns_command_result(self, runner):
        """Test that invite_student returns CommandResult with proper fields."""
        with patch.object(runner, 'run_command', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(
                exit_code=0,
                stdout='{"email":"test@test.com","objectId":"123","userType":"member","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}',
                stderr='',
                command='./avd-lab.sh invite-student --email test@test.com',
                success=True
            )
            
            result = await runner.invite_student("test@test.com")
            
            assert result.exit_code == 0
            assert result.success is True
            assert "test@test.com" in result.stdout


# === Integration Tests ===

class TestStudentOnboardingFlow:
    """Integration tests for student onboarding flow."""

    def test_flow_existing_member_user(self, parser):
        """Test complete flow for existing member user."""
        output = """[INFO] Processing student: member@university.edu
[INFO] Looking up existing user: member@university.edu
[INFO] Found existing user: member@university.edu (Object ID: member-uuid-123, Type: member)
[INFO] User member@university.edu is an existing user
{"email":"member@university.edu","objectId":"member-uuid-123","userType":"member","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        # Verify all expected fields
        assert result.success is True
        assert result.email == "member@university.edu"
        assert result.object_id == "member-uuid-123"
        assert result.user_type == "member"
        assert result.provisioning_action == "existing_user"

    def test_flow_existing_guest_user(self, parser):
        """Test complete flow for existing guest user."""
        output = """[INFO] Processing student: guest@partner.org
[INFO] Looking up existing user: guest@partner.org
[INFO] Found existing user: guest@partner.org (Object ID: guest-uuid-456, Type: guest)
[INFO] User guest@partner.org is an existing user
{"email":"guest@partner.org","objectId":"guest-uuid-456","userType":"guest","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "guest@partner.org"
        assert result.object_id == "guest-uuid-456"
        assert result.user_type == "guest"
        assert result.provisioning_action == "existing_user"

    def test_flow_new_invite(self, parser):
        """Test complete flow for new user invitation."""
        output = """[INFO] Processing student: newuser@newdomain.com
[INFO] Looking up existing user: newuser@newdomain.com
[INFO] User not found. Inviting new user: newuser@newdomain.com
[SUCCESS] Invited student newuser@newdomain.com (Object ID: new-invite-789)
{"email":"newuser@newdomain.com","objectId":"new-invite-789","userType":"guest","provisioningAction":"invited","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.email == "newuser@newdomain.com"
        assert result.object_id == "new-invite-789"
        assert result.user_type == "guest"
        assert result.provisioning_action == "invited"

    def test_flow_invite_with_retry_lookup(self, parser):
        """Test flow where invite returns no ID but lookup succeeds after retry."""
        output = """[INFO] Processing student: retry@example.com
[INFO] Looking up existing user: retry@example.com
[INFO] User not found. Inviting new user: retry@example.com
[INFO] Object ID not in invite response, resolving via lookup...
[INFO] Retry 3/5: looking up retry@example.com
[SUCCESS] Invited student retry@example.com
{"email":"retry@example.com","objectId":"retry-resolved-111","userType":"guest","provisioningAction":"invited","status":"success","errorCode":"","errorMessage":""}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is True
        assert result.object_id == "retry-resolved-111"

    def test_flow_permission_denied(self, parser):
        """Test flow for permission denied error."""
        output = """[ERROR] Failed to invite student: Authorization_RequestDenied - Insufficient privileges
{"email":"noperms@example.com","objectId":"","userType":"","provisioningAction":"invite_failed","status":"error","errorCode":"403","errorMessage":"Authorization_RequestDenied - Insufficient privileges"}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is False
        assert result.status == "error"
        assert result.error_code == "403"
        assert "Insufficient privileges" in result.error_message

    def test_flow_user_unresolved(self, parser):
        """Test flow for user unresolved timeout."""
        output = """[ERROR] Failed to resolve Object ID after invitation
{"email":"unresolved@example.com","objectId":"","userType":"","provisioningAction":"invite_failed","status":"error","errorCode":"1","errorMessage":"Failed to resolve Object ID after invitation"}"""
        
        result = parser.parse_student_invite(output)
        
        assert result.success is False
        assert result.status == "error"
        assert result.provisioning_action == "invite_failed"
        assert "Failed to resolve Object ID" in result.error_message


# === JSON Contract Verification Tests ===

class TestStudentJsonContract:
    """Tests to verify strict JSON contract compliance."""

    def test_json_contract_fields_present(self, parser):
        """Verify all required JSON fields are present in output."""
        output = '{"email":"test@test.com","objectId":"abc-123","userType":"member","provisioningAction":"existing_user","status":"success","errorCode":"","errorMessage":""}'
        
        result = parser.parse_student_invite(output)
        
        # Verify all contract fields
        assert hasattr(result, 'email')
        assert hasattr(result, 'object_id')
        assert hasattr(result, 'user_type')
        assert hasattr(result, 'provisioning_action')
        assert hasattr(result, 'status')
        assert hasattr(result, 'error_code')
        assert hasattr(result, 'error_message')
        assert hasattr(result, 'success')

    def test_json_contract_error_case(self, parser):
        """Verify JSON contract works for error cases."""
        output = '{"email":"err@test.com","objectId":"","userType":"","provisioningAction":"invite_failed","status":"error","errorCode":"500","errorMessage":"Server error"}'
        
        result = parser.parse_student_invite(output)
        
        assert result.email == "err@test.com"
        assert result.status == "error"
        assert result.error_code == "500"
        assert result.error_message == "Server error"
        assert result.success is False
