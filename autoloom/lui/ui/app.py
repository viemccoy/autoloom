from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Input, Select, Button, Static
import asyncio
import pyperclip
import os
import re
from dotenv import load_dotenv

from .components.generation_box import GenerationBox
from .components.completion_overlay import CompletionOverlay
from .components.quit_overlay import QuitConfirmationOverlay
from .generation_manager import GenerationManager

load_dotenv()

def get_classifier_models():
    """Load classifier models from .env file"""
    classifier_models = [
        ("GPT-4.1", "gpt-4.1"),  # Add the new GPT-4.1 model
        ("Default GPT-4", os.getenv("DEFAULT_CLASSIFIER", "gpt-4")),  # Use DEFAULT_CLASSIFIER or fall back to gpt-4
    ]
    
    # Scan .env for custom classifier models (keys starting with CLASSIFIER_ or ending with _CLASSIFIER)
    for key, value in os.environ.items():
        if key.startswith("CLASSIFIER_") or (key.endswith("_CLASSIFIER") and key != "DEFAULT_CLASSIFIER"):
            # Format the display name by removing prefix/suffix and converting to title case
            if key.startswith("CLASSIFIER_"):
                display_name = key[11:].replace("_", " ").title()
            else:  # ends with _CLASSIFIER
                display_name = key[:-10].replace("_", " ").title()
                
            classifier_models.append((f"{display_name} Classifier", value))
    
    return classifier_models

ASCII_ART = """   _____    __    __    _______    _____    __       _____      _____     __    __   
  /\___/\  /\_\  /_/\ /\_______)\ ) ___ (  /\_\     ) ___ (    ) ___ (   /_/\  /\_\  
 / / _ \ \( ( (  ) ) )\(___  __\// /\_/\ \( ( (    / /\_/\ \  / /\_/\ \  ) ) \/ ( (  
 \ \(_)/ / \ \ \/ / /   / / /   / /_/ (_\ \\ \_\  / /_/ (_\ \/ /_/ (_\ \/_/ \  / \_\ 
 / / _ \ \  \ \  / /   ( ( (    \ \ )_/ / // / /__\ \ )_/ / /\ \ )_/ / /\ \ \\// / / 
( (_( )_) ) ( (__) )    \ \ \    \ \/_\/ /( (_____(\ \/_\/ /  \ \/_\/ /  )_) )( (_(  
 \/_/ \_\/   \/__\/     /_/_/     )_____(  \/_____/ )_____(    )_____(   \_\/  \/_/  
                                                                                     """

class AUTOLOOM(App):
    CSS_PATH = "styles.css"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+s", "show_completion", "Show Full Completion"), 
    ]

    def __init__(self):
        super().__init__()
        self.generation_manager = GenerationManager(self)
        self._status_task = None
        self.is_closing = False

    async def action_quit(self) -> None:
        """Show quit confirmation overlay"""
        self.push_screen(QuitConfirmationOverlay(self.generation_manager.completion_history))

    def action_show_completion(self) -> None:
        """Show the full completion overlay with history without copying"""
        if self.generation_manager.completion_history:
            full_history = "Original Prompt:\n" + self.generation_manager.original_prompt + "\n\n"
            for i, entry in enumerate(self.generation_manager.completion_history, 1):
                full_history += f"Completion {i} (score: {entry['score']}):\n{entry['result']}\n\n"
            self.push_screen(CompletionOverlay(full_history))
        else:
            prompt_input = self.query_one("#prompt-input")
            if prompt_input and prompt_input.value:
                self.push_screen(CompletionOverlay(prompt_input.value))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(ASCII_ART, id="ascii-art"),
            Static("LUI v0.0.2, by VIE MCCOY and Morpheus Systems", id="version"),
            Container(
                Input(placeholder="Enter your prompt...", id="prompt-input"),
                Select([
                    ("Llama-405b Base", "meta-llama/Meta-Llama-3.1-405B"),
                    ("GPT-4 Base", "gpt-4-base"),
                    ("GPT-3.5 Turbo Instruct", "gpt-3.5-turbo-instruct")
                ], prompt="Select Generation Model", id="generation-model-select", value="meta-llama/Meta-Llama-3.1-405B"),
                Select(
                    get_classifier_models(),
                    prompt="Select Classification Model", 
                    id="classifier-model-select", 
                    value=os.getenv("DEFAULT_CLASSIFIER", "gpt-4")
                ),
                Container(
                    Input(placeholder="Temperature (0.0-1.0)", value="0.7", id="temp-input"),
                    Input(placeholder="Max Tokens", value="100", id="tokens-input"),
                    Input(placeholder="Number of Generations", value="5", id="gen-count-input"),
                    Input(placeholder="Wait Time (s)", value="10", id="wait-time-input"),
                    id="settings"
                ),
                Button("Generate", id="generate-btn"),
                id="input-container"
            ),
            Container(
                Vertical(id="generations"),
                Static("Ready", id="timer"),
                id="generation-view",
                classes="hidden"
            ),
            id="main-container"
        )
        yield Footer()

    async def animate_status(self, text: str):
        """Animate status text with dots"""
        timer = self.query_one("#timer")
        dots = 0
        while True:
            try:
                status = f"【 {text}{'.' * dots} 】"  # Cyberpunk-style brackets
                timer.update(status)
                dots = (dots + 1) % 4
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break

    async def update_status(self, text: str):
        """Update status with animation"""
        if self._status_task:
            self._status_task.cancel()
            await asyncio.sleep(0.1)  # Allow cancellation to process
        self._status_task = asyncio.create_task(self.animate_status(text))

    def on_mount(self):
        """Initialize UI elements on mount"""
        self.input_container = self.query_one("#input-container")
        self.generation_view = self.query_one("#generation-view")

    def show_input_view(self):
        """Show the input view"""
        self.input_container.remove_class("hidden")
        self.generation_view.add_class("hidden")

    def show_generation_view(self):
        """Show the generation view"""
        self.input_container.add_class("hidden")
        self.generation_view.remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events"""
        # Only handle generate button events at app level
        if event.button.id == "generate-btn":
            asyncio.create_task(self.generation_manager.generate())
            event.stop()  # Stop event propagation

    async def on_unmount(self):
        """Cleanup on app shutdown"""
        self.is_closing = True
        if self._status_task:
            self._status_task.cancel()
        await self.generation_manager.close()