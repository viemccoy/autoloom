from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Input, Select, Button, Static
import asyncio
from lui.models.generator import Generator
from textual.screen import Screen
from textual.screen import Screen
from textual.widgets import Button
import pyperclip

ASCII_ART = """    ___    __  __  ______   ____     __    ____    ____     __  ___
   /   |  / / / / /_  __/  / __ \   / /   / __ \  / __ \   /  |/  /
  / /| | / / / /   / /    / / / /  / /   / / / / / / / /  / /|_/ / 
 / ___ |/ /_/ /   / /    / /_/ /  / /___/ /_/ / / /_/ /  / /  / /  
/_/  |_|\____/   /_/     \____/  /_____/\____/  \____/  /_/  /_/   
                                                                   """

class GenerationBox(Static):
    """A box to display generated text with optional winner styling"""
    def __init__(self, text: str, winner: bool = False):
        super().__init__()
        self.text = text
        self.winner = winner

    def render(self):
        return f"👑 {self.text}" if self.winner else self.text

    def on_mount(self):
        self.add_class("winner-box" if self.winner else "generation-box")

class CompletionOverlay(Screen):
    """Overlay screen for showing the full completion"""
    
    def __init__(self, completion_text: str):
        super().__init__()
        self.completion_text = completion_text

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Container(
                    Static(self.completion_text, id="completion-text"),
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

class QuitConfirmationOverlay(Screen):
    """Overlay screen for confirming quit and offering to copy state"""
    
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
                Static("Do you want to copy the session history before quitting?"),
                Static(full_state, id="quit-state-text"),
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

class AutoloomApp(App):
    CSS_PATH = "styles.css"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+s", "show_completion", "Show Full Completion"),
        ("ctrl+space", "interrupt", "")  # Add this binding
    ]
    
    def __init__(self):
        super().__init__()
        self.generator = Generator()
        self.generations = []
        self.interrupted = False  # Add this flag
        self.original_prompt = ""
        self._status_task = None
        self.is_closing = False
        self.completion_history = []
    
    def action_interrupt(self):
        """Handle interrupt action"""
        self.interrupted = True
    async def action_quit(self):
        """Handle quit action"""
        self.push_screen(QuitConfirmationOverlay(self.completion_history))

    def action_show_completion(self) -> None:
        """Show the full completion overlay with history"""
        if self.completion_history:
            full_history = "Original Prompt:\n" + self.original_prompt + "\n\n"
            for i, entry in enumerate(self.completion_history, 1):
                full_history += f"Completion {i} (score: {entry['score']}):\n{entry['result']}\n\n"
            self.push_screen(CompletionOverlay(full_history))
        else:
            prompt_input = self.query_one("#prompt-input")
            if prompt_input and prompt_input.value:
                self.push_screen(CompletionOverlay(prompt_input.value))

    async def on_unmount(self):
        """Cleanup on app shutdown"""
        self.is_closing = True
        if self._status_task:
            self._status_task.cancel()
        await self.generator.close()
    
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        yield Container(
            Static(ASCII_ART, id="ascii-art"),
            Static("v0.0.1, by Morpheus Systems", id="version"),
            Container(
                Input(placeholder="Enter your prompt...", id="prompt-input"),
                Select([(
                    "Default Classifier",
                    "gpt-4o"
                )], prompt="Select Model", id="model-select"),
                Container(
                    Input(placeholder="Temperature (0.0-1.0)", value="0.7", id="temp-input"),
                    Input(placeholder="Max Tokens", value="100", id="tokens-input"),
                    Input(placeholder="Number of Generations", value="5", id="gen-count-input"),
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
                timer.update("【 Ready 】")
                break
    # Find and replace the following section in app.py

    async def prompt_manual_selection(self):
        """Prompt user to choose their favorite completion"""
        generations_container = self.query_one("#generations")
        timer = self.query_one("#timer")

        # Display available completions with clear numbers
        generations_container.remove_children()
        for idx, text in enumerate(self.generations, 1):
            generations_container.mount(
                GenerationBox(f"{idx}. {text}")
            )
        
        timer.update("Enter number of preferred completion (1-{})".format(len(self.generations)))
        
        while True:
            try:
                # Add input handling directly in the UI
                prompt = "Enter completion number (1-{}): ".format(len(self.generations))
                with self.suspend():
                    choice = input(prompt)
                
                idx = int(choice) - 1
                if 0 <= idx < len(self.generations):
                    chosen_completion = self.generations[idx]
                    prompt_input = self.query_one("#prompt-input")
                    if prompt_input:
                        self.completion_history.append({
                            'prompt': self.original_prompt if not self.completion_history else self.completion_history[-1]['result'],
                            'result': chosen_completion,
                            'score': -1  # Manual selection doesn't have a score
                        })
                        prompt_input.value = chosen_completion
                        self.show_input_view()
                        return
                else:
                    timer.update(f"Please enter a number between 1 and {len(self.generations)}")
            except ValueError:
                timer.update("Please enter a valid number")

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

    def action_interrupt(self):
        """Handle interrupt action"""
        self.interrupted = True

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events"""
        if event.button.id == "generate-btn":
            asyncio.create_task(self.generate_text())

    async def generate_text(self):
        """Main text generation workflow"""
        try:
            self.interrupted = False
            generations_container = self.query_one("#generations")
            generations_container.remove_children()
            self.show_generation_view()
            
            # Get input values
            prompt = self.query_one("#prompt-input").value
            temperature = float(self.query_one("#temp-input").value)
            max_tokens = int(self.query_one("#tokens-input").value)
            num_generations = int(self.query_one("#gen-count-input").value)
            
            if not self.original_prompt:
                self.original_prompt = prompt

            # Generation phase
            await self.update_status("Generating")
            self.generations = []
            
            for i in range(num_generations):
                if i > 0:  # Don't delay before the first generation
                    await asyncio.sleep(0.5)
                
                gen = await self.generator.generate_one(
                    prompt, 
                    max_tokens, 
                    temperature,
                    is_first_of_round=(i == 0)
                )
                
                # Check for invalid characters or errors
                try:
                    gen.encode('utf-8').decode('utf-8')
                    if any(char.encode('utf-8') == b'\xef\xbf\xbd' for char in gen):
                        raise ValueError("Invalid character detected")
                except (UnicodeError, ValueError):
                    continue  # Retry this generation
                
                if gen.startswith(("Error:", "Error in generation:")):
                    if "Maximum retries" in gen:
                        generations_container.mount(GenerationBox(
                            "💥 Generation failed after maximum retries - rate limit exceeded"
                        ))
                        await asyncio.sleep(1)
                        continue
                    elif "Too many requests" in gen:
                        continue  # Will be handled by retry logic in generate_one
                    else:
                        generations_container.mount(GenerationBox(f"💥 {gen}"))
                        await asyncio.sleep(1)
                        continue

                self.generations.append(gen)
                generations_container.remove_children()
                for idx, text in enumerate(self.generations, 1):
                    generations_container.mount(
                        GenerationBox(f"Generation {idx}: {text}")
                    )
                await asyncio.sleep(0.5)

            if not self.generations:
                await self.update_status("No successful generations")
                self.show_input_view()
                return

            # Scoring phase
            await self.update_status("Scoring all generations in parallel")
            generations_container.remove_children()

            gen_boxes = []
            for idx, text in enumerate(self.generations):
                box = GenerationBox(f"Generation {idx+1}: {text} (Awaiting score...)")
                generations_container.mount(box)
                gen_boxes.append(box)

            async def update_score(idx: int, score: int):
                gen_boxes[idx].text = f"Generation {idx+1} (score: {score}): {self.generations[idx]}"
                gen_boxes[idx].refresh()
                scored_count = sum(1 for box in gen_boxes if "score:" in box.text)
                await self.update_status(f"Scored {scored_count}/{len(self.generations)} generations")

            scored_generations = await self.generator.classify(self.generations, update_score)

            # Show winner
            await self.update_status("Ranking complete")
            generations_container.remove_children()
            chosen_idx, chosen_score = scored_generations[0]
            generations_container.mount(
                GenerationBox(
                    f"Selected output (score: {chosen_score}): {self.generations[chosen_idx]}",
                    winner=True
                )
            )

            # Show other generations
            for idx, score in scored_generations[1:]:
                generations_container.mount(
                    GenerationBox(f"Generation {idx+1} (score: {score}): {self.generations[idx]}")
                )

            # Cancel any existing status animation before countdown
            if self._status_task:
                self._status_task.cancel()
                await asyncio.sleep(0.1)

            # Countdown phase
            timer = self.query_one("#timer")
            try:
                #timer.update("Press Ctrl+Space to choose your own favorite")
                
                for i in range(10, 0, -1):
                    if self.interrupted:
                        timer.update("Interrupted! Choose your preferred completion:")
                        await self.prompt_manual_selection()
                        return  # End this generation cycle after manual selection
                    
                    # timer.update(f"Continuing with selected generation in {i}... (Ctrl+Space to interrupt)")
                    timer.update(f"Continuing with selected generation in {i}...") # add ctrl+space back when functionality is restored
                    await asyncio.sleep(1)
            
                # If we get here, no interruption occurred
                prompt_input = self.query_one("#prompt-input")
                if prompt_input:
                    chosen_completion = self.generations[chosen_idx]
                    self.completion_history.append({
                        'prompt': self.original_prompt if not self.completion_history else self.completion_history[-1]['result'],
                        'result': chosen_completion,
                        'score': chosen_score
                    })
                    prompt_input.value = chosen_completion
                    self.show_input_view()
                    await self.generate_text()

            except Exception as e:
                if not self.is_closing:  # Only handle errors if app is still running
                    timer.update(f"Error during countdown: {str(e)}")
                    self.show_input_view()

        except Exception as e:
            if not self.is_closing:  # Only handle errors if app is still running
                await self.update_status(f"Error: {str(e)}")
                self.show_input_view()

    async def on_unmount(self):
        """Cleanup on app shutdown"""
        if self._status_task:
            self._status_task.cancel()
        await self.generator.close()