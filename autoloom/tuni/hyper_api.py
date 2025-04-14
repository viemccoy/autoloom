from openai import AsyncOpenAI
from typing import List, Optional
from .client_types import BaseClient

class HyperBaseClient(BaseClient):
    def __init__(self, config: dict):
        if not config['HYPERBOLIC_API_KEY']:
            raise ValueError('HYPERBOLIC_API_KEY is not set in the config')
            
        self.client = AsyncOpenAI(
            api_key=config['HYPERBOLIC_API_KEY'],
            base_url='https://api.hyperbolic.xyz/v1'
        )

    async def multiQuery(self, 
                        prompt: str, 
                        max_tokens: int, 
                        n: int, 
                        stop: Optional[str] = None) -> List[str]:
        """Generate multiple completions for a given prompt"""
        params = {
            'model': 'meta-llama/Meta-Llama-3.1-405B',
            'prompt': prompt,
            'max_tokens': max_tokens,
            'n': n,
            'stop': stop,
            'temperature': 1.0
        }
        
        try:
            response = await self.client.completions.create(**params)
            return [choice.text for choice in response.choices if choice.text]
        except Exception as e:
            print(f"Error in multiQuery: {str(e)}")
            return [f"Error: {str(e)}"] * n
            
    async def close(self):
        """Close the client session"""
        await self.client.close()