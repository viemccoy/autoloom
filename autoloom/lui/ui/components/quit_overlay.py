from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, Button
import pyperclip
from textual.app import ComposeResult

class QuitConfirmationOverlay(Screen):
    def __init__(self, completion_history):
        super().__init__()
        self.completion_history = completion_history

    def compose(self) -> ComposeResult:
        full_state = "Session History:\n\n"
        if self.completion_history:
            for i, entry in enumerate(self.completion_history, 1):
                full_state += f"Step {i}:\n"
                full_state += f"Prompt: {entry['prompt']}\n"
                full_state += f"Completion: {entry['result']}\n"
                full_state += f"Score: {entry['score']}\n\n"
        
        yield Container(
            Container(
                Container(
                    Static("Do you want to copy the session history before quitting?"),
                    Static(full_state, id="quit-state-text"),
                    id="scroll-container"
                ),
                Container(
                    Button("Copy & Quit", id="copy-quit-btn"),
                    Button("Just Quit", id="just-quit-btn"),
                    Button("Cancel", id="cancel-quit-btn"),
                    id="quit-buttons"
                ),
                id="quit-content"
            ),
            id="quit-overlay"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-quit-btn":
            pyperclip.copy(self.query_one("#quit-state-text").render())
            self.app.exit()
        elif event.button.id == "just-quit-btn":
            self.app.exit()
        elif event.button.id == "cancel-quit-btn":
            self.app.pop_screen()