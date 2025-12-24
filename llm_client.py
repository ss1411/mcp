import os
from typing import List, Dict
from openai import OpenAI

OPENAI_MODEL = "gpt-4o-mini"  # text-capable, low-cost model


class LLMClient:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required.")
        self.client = OpenAI(api_key=api_key)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Call OpenAI Chat Completions with gpt-4o-mini and return the assistant text.
        The messages list is in the usual {'role': 'user'|'assistant'|'system', 'content': str} format.
        """
        completion = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages, # system message along with tool context and user query from app.py
            temperature=0.3, # lower temperature for customer support use case
        )
        return completion.choices[0].message.content or ""
