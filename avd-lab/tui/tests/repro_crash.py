from textual.app import App
from widgets.create_form import CreateLabForm
import asyncio

async def run_repro():
    app = App()
    
    # We need to simulate the app structure slightly to push the screen
    async with app.run_test() as pilot:
        form = CreateLabForm()
        await app.push_screen(form)
        
        # Simulate typing into participant input
        input_widget = form.query_one("#participant-input")
        input_widget.value = "t"
        
        # This should trigger on_input_changed -> self.participant = ...
        # If it crashes, it will raise exception here

import asyncio
if __name__ == "__main__":
    try:
        asyncio.run(run_repro())
        print("No crash detected")
    except Exception as e:
        print(f"Caught expected crash: {e}")
        import traceback
        traceback.print_exc()
