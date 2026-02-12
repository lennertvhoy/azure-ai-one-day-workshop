import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.cli_runner import CliRunner, ExitCode

@pytest.fixture
def runner():
    with patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True):
        yield CliRunner()

@pytest.mark.asyncio
async def test_create_arguments_basic(runner):
    with patch.object(runner, 'run_command', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.exit_code = 0
        
        await runner.create(
            config_path="/abs/path/config.json",
            participant="user1",
            ttl="8h"
        )
        
        args = mock_run.call_args[0]
        # args[0] is "create"
        # args[1:] are the flags
        cmd_args = list(args)
        assert cmd_args[0] == "create"
        assert "--config" in cmd_args
        assert "--participant" in cmd_args
        assert "--subscription" not in cmd_args

@pytest.mark.asyncio
async def test_create_arguments_full(runner):
    with patch.object(runner, 'run_command', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.exit_code = 0
        
        await runner.create(
            config_path="/abs/path/config.json",
            participant="user1",
            ttl="8h",
            subscription_id="sub-123",
            rg_mode="existing",
            rg_name="rg-existing"
        )
        
        args = mock_run.call_args[0]
        cmd_args = list(args)
        
        assert "--subscription" in cmd_args
        assert cmd_args[cmd_args.index("--subscription") + 1] == "sub-123"
        
        assert "--rg-mode" in cmd_args
        assert cmd_args[cmd_args.index("--rg-mode") + 1] == "existing"
        
        assert "--rg-name" in cmd_args
        assert cmd_args[cmd_args.index("--rg-name") + 1] == "rg-existing"

@pytest.mark.asyncio
async def test_list_subscriptions(runner):
    mock_output = '[{"id": "sub1", "name": "Subscription 1"}]'
    
    with patch('asyncio.create_subprocess_exec') as mock_exec:
        process = AsyncMock()
        process.communicate.return_value = (mock_output.encode(), b'')
        process.returncode = 0
        mock_exec.return_value = process
        
        subs = await runner.list_subscriptions()
        
        assert len(subs) == 1
        assert subs[0]['id'] == "sub1"
        assert subs[0]['name'] == "Subscription 1"

@pytest.mark.asyncio
async def test_list_resource_groups(runner):
    mock_output = '[{"name": "rg1", "location": "eastus"}]'
    
    with patch('asyncio.create_subprocess_exec') as mock_exec:
        process = AsyncMock()
        process.communicate.return_value = (mock_output.encode(), b'')
        process.returncode = 0
        mock_exec.return_value = process
        
        rgs = await runner.list_resource_groups(subscription_id="sub1")
        
        assert len(rgs) == 1
        assert rgs[0]['name'] == "rg1"
