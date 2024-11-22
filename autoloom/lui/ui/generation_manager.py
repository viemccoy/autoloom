import asyncio
from typing import Dict, Any, Tuple
from ..models.generator import Generator
from .components.generation_box import GenerationBox

class GenerationManager:
    def __init__(self, app):
        self.app = app
        self.generator = Generator()
        self.generations = []
        self.original_prompt = ""
        self.completion_history = []
        self._status_task = None
        self.is_closing = False
        self.wait_time = 10

    async def update_status(self, text: str):
        """Delegate status updates to the app"""
        await self.app.update_status(text)

    async def get_input_values(self) -> Dict[str, Any]:
        """Get input values from UI elements"""
        return {
            'prompt': self.app.query_one("#prompt-input").value,
            'generation_model': self.app.query_one("#generation-model-select").value,
            'classifier_model': self.app.query_one("#classifier-model-select").value,
            'temperature': float(self.app.query_one("#temp-input").value),
            'max_tokens': int(self.app.query_one("#tokens-input").value),
            'num_generations': int(self.app.query_one("#gen-count-input").value),
            'wait_time': int(self.app.query_one("#wait-time-input").value)
        }

    async def perform_generation_phase(self, inputs: Dict[str, Any]) -> bool:
        """Handle the text generation phase"""
        await self.update_status("Generating in batch")
        self.generations = await self.generator.generate_batch(
            inputs['prompt'],
            inputs['generation_model'],
            inputs['max_tokens'],
            inputs['temperature'],
            inputs['num_generations']
        )

        if not self.generations or all(g.startswith("Error:") for g in self.generations):
            await self.update_status("No successful generations")
            self.app.show_input_view()
            return False
        return True

    async def perform_scoring_phase(self, classifier_model: str):
        """Handle the scoring phase"""
        await self.update_status("Scoring all generations in parallel")
        generations_container = self.app.query_one("#generations")
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

        return await self.generator.classify(self.generations, classifier_model, update_score)

    async def display_results(self, scored_generations) -> Tuple[int, int]:
        """Display the generation results"""
        generations_container = self.app.query_one("#generations")
        generations_container.remove_children()
        
        chosen_idx, chosen_score = scored_generations[0]
        generations_container.mount(
            GenerationBox(
                f"Selected output (score: {chosen_score}): {self.generations[chosen_idx]}",
                winner=True
            )
        )

        for idx, score in scored_generations[1:]:
            generations_container.mount(
                GenerationBox(f"Generation {idx+1} (score: {score}): {self.generations[idx]}")
            )

        return chosen_idx, chosen_score

    async def handle_countdown(self, chosen_idx: int, chosen_score: int) -> bool:
        """Handle countdown and selection process"""
        for i in range(self.wait_time, 0, -1):
            await self.update_status(f"Continuing with selected generation in {i}")
            await asyncio.sleep(1)

        prompt_input = self.app.query_one("#prompt-input")
        if prompt_input:
            chosen_completion = self.generations[chosen_idx]
            self.completion_history.append({
                'prompt': self.original_prompt if not self.completion_history else self.completion_history[-1]['result'],
                'result': chosen_completion,
                'score': chosen_score
            })
            prompt_input.value = chosen_completion
            self.app.show_input_view()
            return True
        return False

    async def generate(self):
        """Main generation orchestration"""
        try:
            generations_container = self.app.query_one("#generations")
            generations_container.remove_children()
            self.app.show_generation_view()

            inputs = await self.get_input_values()

            self.wait_time = inputs['wait_time']

            
            if not self.original_prompt:
                self.original_prompt = inputs['prompt']

            if not await self.perform_generation_phase(inputs):
                return

            scored_generations = await self.perform_scoring_phase(inputs['classifier_model'])
            chosen_idx, chosen_score = await self.display_results(scored_generations)

            if self._status_task:
                self._status_task.cancel()
                await asyncio.sleep(0.1)

            if await self.handle_countdown(chosen_idx, chosen_score):
                await self.generate()

        except Exception as e:
            if not self.is_closing:
                await self.update_status(f"Error: {str(e)}")
                self.app.show_input_view()

    async def close(self):
        """Cleanup resources"""
        if hasattr(self, 'classifier') and self.classifier is not None:
            await self.classifier.close()
        self.is_closing = True
        if self._status_task:
            self._status_task.cancel()
        await self.generator.close()