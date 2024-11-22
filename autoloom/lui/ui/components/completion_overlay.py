from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, Button
import pyperclip
from textual.app import ComposeResult

class CompletionOverlay(Screen):
    def __init__(self, completion_text: str):
        super().__init__()
        self.completion_text = completion_text

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Container(
                    Static(self.completion_text, id="completion-text", markup=False),  # Add markup=False
                    id="scroll-container"
                ),
                Container(
                    Button("Copy", id="copy-btn"),
                    Button("Return", id="return-btn"),
                    id="overlay-buttons"
                ),
                id="overlay-content"
            ),
            id="overlay"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-btn":
            pyperclip.copy(self.completion_text)
        elif event.button.id == "return-btn":
            self.app.pop_screen()