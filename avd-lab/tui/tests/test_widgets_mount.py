import pytest
from textual.app import App
from widgets.create_form import CreateLabForm
from widgets.destroy_confirm import DestroyConfirmDialog
from widgets.log_panel import LogPanel
from widgets.validation_view import ValidationView

from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_create_form_mount():
    """Test that CreateLabForm mounts without error."""
    app = App()
    
    mock_runner = MagicMock()
    mock_runner.list_subscriptions = AsyncMock(return_value=[])
    
    async with app.run_test():
        form = CreateLabForm(cli_runner=mock_runner)
        await app.push_screen(form)
        assert form.is_mounted
        assert form.query_one("#config-input")

@pytest.mark.asyncio
async def test_destroy_confirm_mount():
    """Test that DestroyConfirmDialog mounts without error."""
    app = App()
    async with app.run_test():
        dialog = DestroyConfirmDialog()
        await app.push_screen(dialog)
        assert dialog.is_mounted
        assert dialog.query_one("#destroy-btn")

@pytest.mark.asyncio
async def test_log_panel_mount():
    """Test that LogPanel mounts without error."""
    app = App()
    async with app.run_test():
        panel = LogPanel()
        await app.push_screen(panel)
        assert panel.is_mounted

@pytest.mark.asyncio
async def test_validation_view_mount():
    """Test that ValidationView mounts without error."""
    app = App()
    async with app.run_test():
        view = ValidationView()
        await app.push_screen(view)
        assert view.is_mounted
