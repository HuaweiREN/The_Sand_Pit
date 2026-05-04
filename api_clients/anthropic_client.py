"""
The Sand Pit - Anthropic SDK API Client
Uses Anthropic SDK for API calls (Kimi, Claude, etc.)
"""

import time
from typing import Optional, Dict, Any, Tuple

from . import BaseAPIClient


class AnthropicSDKClient(BaseAPIClient):
    """Anthropic SDK format API client (for Kimi, Claude, etc.)."""

    # Rate limit config
    MIN_REQUEST_INTERVAL = 5.0  # Minimum seconds between requests
    MAX_RETRIES = 3  # Max retries on 429
    RETRY_DELAY_BASE = 2  # Exponential backoff base

    _last_request_time = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.api_key:
            import os
            self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or ""

        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Please install anthropic SDK: pip install anthropic"
            )

        client_kwargs = {"base_url": self.base_url}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        self._client = Anthropic(**client_kwargs)

    def _wait_for_rate_limit(self):
        """Wait for rate limit, ensuring request interval >= MIN_REQUEST_INTERVAL."""
        import threading

        with threading.Lock():
            current_time = time.time()
            time_since_last_request = current_time - AnthropicSDKClient._last_request_time

            if time_since_last_request < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - time_since_last_request
                time.sleep(wait_time)

            AnthropicSDKClient._last_request_time = time.time()

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str], int, float]:
        """
        Call Anthropic SDK API (with rate limiting and retry).

        Returns:
            (raw_content, parsed_json, reasoning_content, tokens_used, latency_ms)
        """
        retry_count = 0

        while retry_count <= self.MAX_RETRIES:
            start_time = time.time()

            self._wait_for_rate_limit()

            try:
                messages = [{"role": "user", "content": user_prompt}]

                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "temperature": self.temperature,
                }

                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self._client.messages.create(**kwargs)

                latency = (time.time() - start_time) * 1000

                if not response.content or len(response.content) == 0:
                    return "Empty response", None, None, 0, latency

                content = response.content[0].text.strip()

                reasoning = None
                if hasattr(response, 'thinking') and response.thinking:
                    reasoning = response.thinking

                tokens_used = 0
                if response.usage:
                    tokens_used = response.usage.output_tokens

                parsed_json, _ = self._extract_json(content)

                return content, parsed_json, reasoning, tokens_used, latency

            except Exception as e:
                latency = (time.time() - start_time) * 1000
                error_msg = str(e)

                if "401" in error_msg:
                    return "401 Unauthorized: Invalid API key", None, None, 0, latency
                elif "429" in error_msg:
                    retry_count += 1
                    if retry_count <= self.MAX_RETRIES:
                        wait_time = self.RETRY_DELAY_BASE ** retry_count
                        print(f"[RateLimit] 429 error, retrying in {wait_time}s ({retry_count}/{self.MAX_RETRIES})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return f"429 Too Many Requests: Rate limited after {self.MAX_RETRIES} retries", None, None, 0, latency
                else:
                    return f"API error: {e}", None, None, 0, latency

        return "Unexpected error: retry logic anomaly", None, None, 0, 0
