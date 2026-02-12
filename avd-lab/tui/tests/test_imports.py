import sys
import os

# Ensure tui directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Verify that all core modules can be imported without error."""
    import app
    import widgets.create_form
    import widgets.destroy_confirm
    import widgets.lab_table
    import widgets.log_panel
    import widgets.validation_view
    import services.cli_runner
    import services.parser
    import services.state
    
    assert True
