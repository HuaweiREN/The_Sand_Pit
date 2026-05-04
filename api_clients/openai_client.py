"""
The Sand Pit - OpenAI Compatible API Client
Supports OpenAI-compatible APIs (DeepSeek, Zhipu, Qwen, etc.)
"""

import time
import requests
from typing import Optional, Dict, Any, Tuple

from . import BaseAPIClient


class OpenAICompatibleClient(BaseAPIClient):
    """OpenAI-compatible API client."""

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str], int, float]:
        """
        Call OpenAI-compatible API.

        Returns:
            (raw_content, parsed_json, reasoning_content, tokens_used, latency_ms)
        """
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "thinking": {"type": "enabled"},
        }

        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens

        try:
            endpoint = self._build_endpoint()

            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                proxies={"http": None, "https": None}
            )

            latency = (time.time() - start_time) * 1000

            if response.status_code == 401:
                return "401 Unauthorized: Invalid API key", None, None, 0, latency
            elif response.status_code == 429:
                return "429 Too Many Requests: Rate limited", None, None, 0, latency
            elif response.status_code == 404:
                return "404 Not Found: Endpoint does not exist", None, None, 0, latency
            elif response.status_code != 200:
                return f"HTTP {response.status_code}: {response.text[:200]}", None, None, 0, latency

            result = response.json()

            if "choices" not in result or len(result["choices"]) == 0:
                return f"Invalid response format: {result}", None, None, 0, latency

            choice = result["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "").strip()

            reasoning = message.get("reasoning_content") or message.get("reasoning")

            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            parsed_json, _ = self._extract_json(content)

            return content, parsed_json, reasoning, tokens_used, latency

        except requests.exceptions.Timeout:
            latency = (time.time() - start_time) * 1000
            return "Request timeout", None, None, 0, latency
        except requests.exceptions.ConnectionError as e:
            latency = (time.time() - start_time) * 1000
            return f"Connection error: {e}", None, None, 0, latency
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return f"Unexpected error: {e}", None, None, 0, latency

    def _build_endpoint(self) -> str:
        """Build API endpoint URL."""
        base = self.base_url

        if "/v1" in base:
            return f"{base}/chat/completions"

        return f"{base}/v1/chat/completions"
