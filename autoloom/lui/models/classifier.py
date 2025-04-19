import os
import aiohttp
import asyncio
from typing import List, Tuple
import json
from dotenv import load_dotenv

load_dotenv()

class Classifier:
    def __init__(self, model="gpt-4"):
        self.url = "https://api.openai.com/v1/chat/completions"
        self.model = model # Using standard GPT-4 model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        self._session = None

    async def get_session(self):
        """Get or create an aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _prepare_classification_prompt(self, text: str) -> List[dict]:
        """Prepare the messages for classification"""
        # For GPT-4.1, use developer role for system prompt
        if self.model == "gpt-4.1":
            return [
                {
                    "role": "developer", 
                    "content": "You are a classifier. Your task is to rate the quality and coherence of text on a scale from 0-100. Respond with ONLY a number, no explanation."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        else:
            # For all other models use the standard system/user roles
            return [
                {
                    "role": "system",
                    "content": "You are a classifier. Your task is to rate the quality and coherence of text on a scale from 0-100. Respond with ONLY a number, no explanation."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

    async def classify_one(self, text: str) -> int:
        """Classify a single piece of text"""
        try:
            data = {
                "model": self.model,
                "messages": self._prepare_classification_prompt(text),
                "temperature": 0,
                "max_tokens": 10,
                "response_format": {"type": "text"}
            }

            session = await self.get_session()
            
            async with session.post(self.url, headers=self.headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"API Error (Status {response.status}): {error_text}")
                    return 50

                try:
                    result = await response.json()
                    if not result.get('choices'):
                        print(f"No choices in response: {result}")
                        return 50
                        
                    content = result['choices'][0]['message']['content'].strip()
                    print(f"Raw score response: {content}")  # Debug print
                    
                    # Extract just the numbers from the content
                    score = int(''.join(filter(str.isdigit, content)))
                    
                    # Ensure score is within bounds
                    score = max(0, min(100, score))
                    print(f"Processed score: {score}")  # Debug print
                    return score
                    
                except (KeyError, ValueError) as e:
                    print(f"Error parsing response: {e}")
                    print(f"Raw response: {json.dumps(result, indent=2)}")
                    return 50

        except Exception as e:
            print(f"Unexpected error in classify_one: {str(e)}")
            return 50

    async def classify_batch(self, texts: List[str], callback=None) -> List[Tuple[int, int]]:
        """Classify multiple texts and return (index, score) tuples sorted by score"""
        scores = []
        tasks = []
        
        # Create tasks with delay between each to avoid rate limiting
        for text in texts:
            tasks.append(self.classify_one(text))
            await asyncio.sleep(0.5)  # Add small delay between requests
        
        for i, future in enumerate(asyncio.as_completed(tasks)):
            try:
                score = await future
                scores.append((i, score))
                if callback:
                    await callback(i, score)
            except Exception as e:
                print(f"Error in batch classification for text {i}: {str(e)}")
                scores.append((i, 50))
                if callback:
                    await callback(i, 50)
        
        # Sort by score in descending order
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None