"""
The Sand Pit - API Clients Module
Unified API client module supporting multiple LLM API formats.
"""

from typing import Optional, Dict, Any, Tuple
from abc import ABC, abstractmethod


class BaseAPIClient(ABC):
    """Base class for API clients."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        timeout: int = 300
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    @abstractmethod
    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str], int, float]:
        """
        Call the API for chat completion.

        Returns:
            (raw_content, parsed_json, reasoning_content, tokens_used, latency_ms)
        """
        pass

    def _extract_json(self, content: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Extract JSON from API response."""
        import json
        import re

        if not content:
            return None, "Empty response"

        content = content.strip()

        # Try direct parsing
        try:
            return json.loads(content), None
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        if "```json" in content:
            try:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str), None
            except (IndexError, json.JSONDecodeError):
                pass
        elif "```" in content:
            try:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str), None
            except (IndexError, json.JSONDecodeError):
                pass

        # Try extracting JSON object from text
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                return json.loads(match), None
            except json.JSONDecodeError:
                continue

        return None, f"Failed to extract JSON from: {content[:200]}..."


from .openai_client import OpenAICompatibleClient
from .anthropic_client import AnthropicSDKClient


def create_api_client(
    api_key: str,
    base_url: str,
    model: str,
    client_type: str = "auto",
    **kwargs
) -> BaseAPIClient:
    """
    Create an API client instance.

    Args:
        api_key: API key
        base_url: API base URL
        model: Model name
        client_type: Client type ("openai", "anthropic", "auto")
        **kwargs: Additional parameters

    Returns:
        BaseAPIClient instance
    """
    # If api_key is empty, try reading from environment variables
    if not api_key:
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("OPENAI_API_KEY") or ""

    if client_type == "auto":
        # Auto-detect type
        if "anthropic" in base_url.lower() or "kimi" in base_url.lower():
            try:
                import anthropic
                client_type = "anthropic"
            except ImportError:
                client_type = "openai"
        else:
            client_type = "openai"

    if client_type == "anthropic":
        return AnthropicSDKClient(api_key, base_url, model, **kwargs)
    else:
        return OpenAICompatibleClient(api_key, base_url, model, **kwargs)


__all__ = [
    'BaseAPIClient',
    'OpenAICompatibleClient',
    'AnthropicSDKClient',
    'create_api_client'
]
