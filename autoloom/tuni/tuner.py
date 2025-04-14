import random
from typing import List, Dict, Any
from .client_types import BaseClient

class ContrastContext:
    def __init__(self, max_tokens: int, breakpoints_per_doc: int, 
                 ai_completions_per_breakpoint: int, client: BaseClient):
        self.max_tokens = max_tokens
        self.breakpoints_per_doc = breakpoints_per_doc
        self.ai_completions_per_breakpoint = ai_completions_per_breakpoint
        self.client = client

def get_system_message() -> Dict[str, str]:
    return {"role": "system", "content": "You are a helpful assistant."}

def get_user_message(ctx: ContrastContext, prefix: str, suffix: str) -> Dict[str, str]:
    return {
        "role": "user",
        "content": f"""I will give you a prefix and a suffix. The prefix is taken from human writing. The suffix is either written by a human or is an AI completion of the prefix. Note that, for every human example I will ask you about, there are {ctx.ai_completions_per_breakpoint} AI examples; adjust your priors accordingly. Please just give a Y or N for the guess; say Y x% of the time if you are x% sure this is a human suffix, for example. The prefix is \"\"\"{prefix}\"\"\". The suffix is \"\"\"{suffix}\"\"\". Now answer just Y or N."""
    }

def mk_fine_tuning_example(ctx: ContrastContext, prefix: str, suffix: str, is_human: bool) -> Dict[str, List]:
    return {
        "messages": [
            get_system_message(),
            get_user_message(ctx, prefix, suffix),
            {"role": "assistant", "content": "Y" if is_human else "N"}
        ]
    }

def get_breakpoints(ctx: ContrastContext, doc: str) -> List[int]:
    return [random.randint(0, len(doc) - ctx.max_tokens) 
            for _ in range(ctx.breakpoints_per_doc)]

def get_human_example(ctx: ContrastContext, doc: str, breakpoint: int) -> Dict:
    return mk_fine_tuning_example(
        ctx, 
        doc[:breakpoint], 
        doc[breakpoint:breakpoint + ctx.max_tokens], 
        True
    )

async def get_ai_examples(ctx: ContrastContext, doc: str, breakpoint: int) -> List[Dict]:
    completions = await ctx.client.multiQuery(
        doc[:breakpoint], 
        ctx.max_tokens,
        ctx.ai_completions_per_breakpoint
    )
    return [mk_fine_tuning_example(ctx, doc[:breakpoint], completion, False) 
            for completion in completions]

async def get_doc_examples(ctx: ContrastContext, doc: str) -> List[Dict]:
    breakpoints = get_breakpoints(ctx, doc)
    all_examples = []
    for breakpoint in breakpoints:
        examples = [get_human_example(ctx, doc, breakpoint)]
        ai_examples = await get_ai_examples(ctx, doc, breakpoint)
        examples.extend(ai_examples)
        all_examples.extend(examples)
    return all_examples

async def get_corpus_examples(ctx: ContrastContext, docs: List[str]) -> List[Dict]:
    all_examples = []
    for doc in docs:
        examples = await get_doc_examples(ctx, doc)
        all_examples.extend(examples)
    return all_examples