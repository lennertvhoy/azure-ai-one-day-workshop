import pytest
from unittest.mock import Mock
from pathlib import Path
from textual.app import App
from widgets.template_manager import TemplateManager
from services.cli_runner import CliRunner

class TestApp(App):
    def __init__(self, screen_to_push):
        super().__init__()
        self.screen_to_push = screen_to_push
        
    def on_mount(self):
        self.push_screen(self.screen_to_push)

@pytest.fixture
def mock_cli(tmp_path):
    cli = Mock(spec=CliRunner)
    # mock config dir to tmp_path
    cli.CONFIG_DIR = str(tmp_path)
    return cli

@pytest.mark.asyncio
async def test_template_manager_mount(mock_cli, tmp_path):
    """Test that TemplateManager mounts and lists files."""
    # Create dummy files
    (tmp_path / "test1.json").write_text("{}")
    (tmp_path / "test2.json").write_text("{}")
    
    manager = TemplateManager(cli_runner=mock_cli)
    app = TestApp(manager)
    
    async with app.run_test() as pilot:
        # Check title
        assert "Template Manager" in str(pilot.app.query_one(".header Label").renderable)
        
        # Check table
        table = pilot.app.query_one("#template-table")
        assert table.row_count == 2
        # Check content
        # col 0 is filename
        rows = [table.get_row_at(i)[0] for i in range(2)]
        assert "test1.json" in rows
        assert "test2.json" in rows

@pytest.mark.asyncio
async def test_template_manager_create(mock_cli, tmp_path):
    """Test creating a new template."""
    (tmp_path / "source.json").write_text('{"foo": "bar"}')
    
    manager = TemplateManager(cli_runner=mock_cli)
    app = TestApp(manager)
    
    async with app.run_test(size=(120, 40)) as pilot:
        # Select first row (source.json)
        await pilot.press("down") # ensure selection? Default is usually first row if present? 
        # Actually DataTable might not auto select. 
        # But cursor_type="row" usually has a cursor.
        # Let's try pressing "c"
        
        # Click create (c)
        await pilot.press("c")
        
        from widgets.template_manager import NewTemplateDialog
        assert isinstance(pilot.app.screen, NewTemplateDialog)
        
        # Type name
        await pilot.press(*"new-copy")
        await pilot.press("enter")
        
        # Check file created
        assert (tmp_path / "new-copy.json").exists()
        assert (tmp_path / "new-copy.json").read_text() == '{"foo": "bar"}'
