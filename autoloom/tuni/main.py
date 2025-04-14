# tuni/main.py
# Standard library imports
from typing import List
import json
import asyncio
from pathlib import Path

# Local imports
from .config import read_config
from .hyper_api import HyperBaseClient
from .tuner import ContrastContext, get_doc_examples

async def read_corpus_from_folder(folder: str) -> List[str]:
    folder_path = Path(folder)
    texts = []
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                texts.append(f.read())
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return texts

async def amain():
    try:
        config = read_config()
        client = HyperBaseClient(config)
        ctx = ContrastContext(
            max_tokens=5,
            breakpoints_per_doc=3,
            ai_completions_per_breakpoint=5,
            client=client
        )
        
        text = input("Enter the text to tune on: ")
        examples = await get_doc_examples(ctx, text)
        
        # Write to JSONL file
        output_path = Path("tunes") / "generated_examples.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
                
        print(f"Generated examples saved to {output_path}")
        
    finally:
        if 'client' in locals():
            await client.close()

def main():
    """Synchronous entry point"""
    try:
        asyncio.get_event_loop().run_until_complete(amain())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Error: {e}")