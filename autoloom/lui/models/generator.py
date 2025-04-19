import os
import aiohttp
import asyncio
import json
from typing import List, Tuple
from .classifier import Classifier
from dotenv import load_dotenv

load_dotenv()

class Generator:
    def __init__(self):
        self.hyperbolic_url = "https://api.hyperbolic.xyz/v1/completions"
        self.openai_url = "https://api.openai.com/v1/completions"
        self.hyperbolic_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('HYPERBOLIC_API_KEY')}"
        }
        self.openai_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        self._session = None
        self.classifier = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def get_session(self):
        """Get or create the aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def reset_session(self):
        """Reset the session between rounds"""
        if self._session:
            await self._session.close()
        self._session = None
        await self.get_session()

    async def generate_batch(self, prompt: str, model: str, max_tokens: int, temperature: float, n: int = 5) -> List[str]:
        # Determine which API to use based on the model
        is_openai_model = model.startswith("gpt-")
        
        data = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "n": n
        }
        
        url = self.openai_url if is_openai_model else self.hyperbolic_url
        headers = self.openai_headers if is_openai_model else self.hyperbolic_headers
        
        wait_time = 1
        max_retries = 5
        attempts = 0
        
        while attempts < max_retries:
            try:
                session = await self.get_session()
                async with session.post(url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    
                    # Validate response
                    try:
                        response_text.encode('utf-8').decode('utf-8')
                        result = await response.json()
                        
                        if response.status == 200 and 'choices' in result:
                            completions = [choice['text'] for choice in result['choices'] if choice.get('text')]
                            if completions:
                                return completions
                    
                    except (UnicodeError, json.JSONDecodeError):
                        pass
                    
                    # If we get here, something went wrong
                    attempts += 1
                    if attempts >= max_retries:
                        return [f"Error: Maximum retries ({max_retries}) exceeded"] * n
                    
                    wait_time = min(wait_time * 2, 32)
                    print(f"Retrying batch. Attempt {attempts}/{max_retries}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                attempts += 1
                if attempts >= max_retries:
                    return [f"Error: Maximum retries ({max_retries}) exceeded - {str(e)}"] * n
                wait_time = min(wait_time * 2, 32)
                print(f"Network error. Attempt {attempts}/{max_retries}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        return [f"Error: Maximum retries ({max_retries}) exceeded"] * n

    async def classify(self, generations: List[str], classifier_model: str, callback=None) -> List[Tuple[int, int]]:
        """Initialize classifier with model and classify generations"""
        self.classifier = Classifier(classifier_model)
        return await self.classifier.classify_batch(generations, callback)

    async def close(self):
        """Close both the generator and classifier sessions"""
        if self._session is not None:
            await self._session.close()
            self._session = None
        if self.classifier is not None:  # Add this check
            await self.classifier.close()