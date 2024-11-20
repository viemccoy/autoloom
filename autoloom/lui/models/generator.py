import os
import aiohttp
import asyncio
from typing import List, Tuple
from .classifier import Classifier
from dotenv import load_dotenv

load_dotenv()

class Generator:
    def __init__(self):
        self.url = "https://api.hyperbolic.xyz/v1/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('HYPERBOLIC_API_KEY')}"
        }
        self._session = None
        self.classifier = Classifier()

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

    async def generate_one(self, prompt: str, max_tokens: int, temperature: float, is_first_of_round: bool = False) -> str:
        # Reset session if this is the first generation of a new round
        if is_first_of_round:
            await self.reset_session()
            
        wait_time = 1  # Reset wait time for each generation
        max_retries = 5
        attempts = 0
        
        while attempts < max_retries:
            data = {
                "prompt": prompt,
                "model": "meta-llama/Meta-Llama-3.1-405B-FP8",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            }
            
            try:
                session = await self.get_session()
                async with session.post(self.url, headers=self.headers, json=data) as response:
                    response_text = await response.text()
                    
                    # Check for invalid UTF-8 characters or error indicators
                    should_retry = False
                    try:
                        # Try to encode/decode to check for invalid characters
                        response_text.encode('utf-8').decode('utf-8')
                        
                        # Check for various error patterns
                        lower_text = response_text.lower()
                        if (any(char.encode('utf-8') == b'\xef\xbf\xbd' for char in response_text) or  # Unknown character
                            "error:" in lower_text or 
                            "too many requests" in lower_text or
                            response.status != 200):
                            should_retry = True
                    except UnicodeError:
                        should_retry = True
                    
                    if should_retry:
                        attempts += 1
                        if attempts >= max_retries:
                            return f"Error: Maximum retries ({max_retries}) exceeded"
                        wait_time = min(wait_time * 2, 32)
                        print(f"Retrying. Attempt {attempts}/{max_retries}. Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    # Try to parse as JSON
                    try:
                        result = await response.json()
                        if 'choices' in result and result['choices']:
                            generated_text = result['choices'][0]['text']
                            if generated_text and len(generated_text.strip()) > 0:
                                return generated_text
                    except:
                        pass  # If JSON parsing fails, we'll retry
                    
                    # If we get here, something went wrong with the response
                    attempts += 1
                    if attempts >= max_retries:
                        return f"Error: Maximum retries ({max_retries}) exceeded"
                    wait_time = min(wait_time * 2, 32)
                    print(f"Invalid response. Attempt {attempts}/{max_retries}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                attempts += 1
                if attempts >= max_retries:
                    return f"Error: Maximum retries ({max_retries}) exceeded"
                wait_time = min(wait_time * 2, 32)
                print(f"Network error. Attempt {attempts}/{max_retries}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
                
        return f"Error: Maximum retries ({max_retries}) exceeded"

    async def classify(self, generations: List[str], callback=None) -> List[Tuple[int, int]]:
        """Classify multiple generations and return (index, score) tuples"""
        return await self.classifier.classify_batch(generations, callback)

    async def close(self):
        """Close both the generator and classifier sessions"""
        if self._session is not None:
            await self._session.close()
            self._session = None
        await self.classifier.close()