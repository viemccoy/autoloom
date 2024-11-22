from textual.widgets import Static

class GenerationBox(Static):
    """A box to display generated text with optional winner styling"""
    def __init__(self, text: str, winner: bool = False):
        super().__init__()
        self.text = text
        self.winner = winner

    def render(self):
        sanitized_text = self.text.replace('[', '\\[').replace(']', '\\]')
        return f"👑 {sanitized_text}" if self.winner else sanitized_text

    def on_mount(self):
        self.add_class("winner-box" if self.winner else "generation-box")