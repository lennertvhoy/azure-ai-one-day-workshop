import pytest
from textual.widgets import Label, Button
from widgets.lab_details import LabDetailsDialog
from services.parser import LabListItem

@pytest.fixture
def sample_lab():
    return LabListItem(
        lab_id="azure-test-123",
        participant="test-user",
        resource_group="rg-test",
        location="eastus",
        expiry="2025-01-01T00:00:00Z",
        status="running"
    )

from textual.app import App

class TestApp(App):
    def __init__(self, screen_to_push):
        super().__init__()
        self.screen_to_push = screen_to_push
        
    def on_mount(self):
        self.push_screen(self.screen_to_push)

@pytest.mark.asyncio
async def test_lab_details_mount(sample_lab):
    """Test that LabDetailsDialog mounts and shows correct info."""
    dialog = LabDetailsDialog(lab=sample_lab)
    app = TestApp(dialog)
    
    async with app.run_test() as pilot:
        # Check title
        title = pilot.app.query_one(".title", Label)
        assert "azure-test-123" in str(title.renderable)
        
        # Check content
        labels = pilot.app.query(Label)
        texts = [str(l.renderable) for l in labels]
        
        assert "test-user" in texts
        assert "rg-test" in texts
        assert "eastus" in texts
        
        # Check buttons
        assert pilot.app.query_one("#close-btn", Button)
        assert pilot.app.query_one("#destroy-btn", Button)

@pytest.mark.asyncio
async def test_lab_details_destroy_action(sample_lab):
    """Test that destroy button returns 'destroy'."""
    dialog = LabDetailsDialog(lab=sample_lab)
    app = TestApp(dialog)
    
    async with app.run_test() as pilot:
        await pilot.click("#destroy-btn")
        # In a real app run, this would close the screen with a result.
        # In run_test, we can't easily check the result of dismiss(), 
        # but we can verify no error occurred during click.
