#!/usr/bin/env python3
"""
API Configuration Switcher
Switch between different LLM providers (OpenAI-compatible, Anthropic-compatible, etc.)

NOTE: API keys are read from environment variables. Never hardcode secrets.
Supported env vars:
  - OPENAI_API_KEY / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY
  - OPENAI_BASE_URL / ANTHROPIC_BASE_URL
"""

import json
import argparse
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "config.json"
BACKUP_FILE = SCRIPT_DIR / "config.json.backup"

# Provider presets (no secrets here — keys are injected from env)
API_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model_name": "deepseek-v4-flash",
        "client_type": "openai",
        "temperature": 0.7,
        "timeout": 30
    },
    "deepseek-pro": {
        "base_url": "https://api.deepseek.com",
        "model_name": "deepseek-v4-pro",
        "client_type": "openai",
        "temperature": 0.7,
        "timeout": 30
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o-mini",
        "client_type": "openai",
        "temperature": 0.7,
        "timeout": 30
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model_name": "claude-sonnet-4-6",
        "client_type": "anthropic",
        "temperature": 0.7,
        "timeout": 30
    }
}


def load_config():
    """Load configuration file."""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    """Save configuration file."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def backup_config():
    """Backup current configuration."""
    if CONFIG_FILE.exists():
        config = load_config()
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    return False


def switch_to_provider(provider: str):
    """Switch to the specified provider preset."""
    if provider not in API_PRESETS:
        print(f"[ERROR] Unknown provider: {provider}")
        print(f"Supported providers: {', '.join(API_PRESETS.keys())}")
        return False

    if backup_config():
        print(f"[OK] Current config backed up to: {BACKUP_FILE}")

    config = load_config()
    api_config = API_PRESETS[provider].copy()

    # Read API key from environment
    client_type = api_config.pop("client_type", "openai")
    api_key = ""
    if client_type == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or ""
    else:
        api_key = os.getenv("OPENAI_API_KEY") or ""

    api_config["api_key"] = api_key
    config['api'] = api_config
    save_config(config)

    print(f"[OK] Switched to {provider.upper()} API preset!")
    print(f"  Format: {client_type.upper()}")
    print(f"  Base URL: {api_config['base_url']}")
    print(f"  Model: {api_config['model_name']}")
    if api_key:
        print(f"  API Key: {api_key[:20]}...")
    else:
        print("  API Key: NOT SET (please configure env var)")

    return True


def show_current():
    """Display current API configuration."""
    config = load_config()
    api = config.get('api', {})

    print("=" * 60)
    print("Current API Configuration")
    print("=" * 60)
    print(f"Base URL: {api.get('base_url', 'N/A')}")
    print(f"Model: {api.get('model_name', 'N/A')}")
    print(f"Temperature: {api.get('temperature', 'N/A')}")
    print(f"Timeout: {api.get('timeout', 'N/A')}")
    key = api.get('api_key', '')
    print(f"API Key: {key[:25]}..." if key else "API Key: NOT SET")
    print("=" * 60)


def restore_backup():
    """Restore configuration from backup."""
    if not BACKUP_FILE.exists():
        print("[ERROR] Backup file not found!")
        return False

    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    save_config(config)
    print("[OK] Configuration restored from backup!")
    return True


def test_api_connection():
    """Test connectivity with the current API configuration."""
    import time
    import requests

    print("=" * 60)
    print("API Connectivity Test")
    print("=" * 60)

    try:
        config = load_config()
        api_config = config.get('api', {})

        api_key = api_config.get('api_key', '')
        base_url = api_config.get('base_url', '')
        model = api_config.get('model_name', '')

        if not api_key:
            print("\n[ERROR] API key is not set. Please configure environment variables.")
            return False

        client_type = "openai"
        if "anthropic" in base_url.lower():
            client_type = "anthropic"

        print(f"\nCurrent config:")
        print(f"  Format: {client_type.upper()}")
        print(f"  Base URL: {base_url}")
        print(f"  Model: {model}")
        print(f"  API Key: {api_key[:20]}...")

        print(f"\nSending test request...")

        if client_type == "openai":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Hello, this is a connectivity test. Please respond with 'OK' only."}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            endpoint = f"{base_url}/chat/completions" if "/v1" in base_url else f"{base_url}/v1/chat/completions"

            start_time = time.time()
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30,
                proxies={"http": None, "https": None}
            )
            latency = (time.time() - start_time) * 1000

            print(f"\nStatus: {response.status_code}")
            print(f"Latency: {latency:.0f}ms")

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0].get("message", {}).get("content", "").strip()
                print(f"Response: {content[:50]}...")
                print("\n" + "=" * 60)
                print("[OK] API connectivity test passed!")
                print("=" * 60)
                return True
            elif response.status_code == 401:
                print("\n[ERROR] Authentication failed (401): Invalid API key")
                return False
            elif response.status_code == 429:
                print("\n[WARN] Rate limited (429): Retry later")
                return False
            else:
                print(f"\n[ERROR] Request failed: {response.text[:200]}")
                return False
        else:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key, base_url=base_url)
                start_time = time.time()
                response = client.messages.create(
                    model=model,
                    max_tokens=10,
                    temperature=0.1,
                    messages=[{"role": "user", "content": "Hello, this is a connectivity test. Please respond with 'OK' only."}]
                )
                latency = (time.time() - start_time) * 1000
                print(f"\nLatency: {latency:.0f}ms")
                if response.content and len(response.content) > 0:
                    content = response.content[0].text.strip()
                    print(f"Response: {content[:50]}...")
                    print("\n" + "=" * 60)
                    print("[OK] API connectivity test passed!")
                    print("=" * 60)
                    return True
                return True
            except ImportError:
                print("\n[ERROR] anthropic SDK not installed: pip install anthropic")
                return False
            except Exception as e:
                print(f"\n[ERROR] Request failed: {e}")
                return False

    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Switch API configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Switch to DeepSeek Flash (OpenAI format)
  python switch_api.py --deepseek

  # Switch to DeepSeek Pro (OpenAI format)
  python switch_api.py --deepseek-pro

  # Switch to OpenAI
  python switch_api.py --openai

  # Show current config
  python switch_api.py --current

  # Restore from backup
  python switch_api.py --restore

  # Test API connectivity
  python switch_api.py --test
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--deepseek", action="store_true", help="Switch to DeepSeek Flash preset")
    group.add_argument("--deepseek-pro", action="store_true", help="Switch to DeepSeek Pro preset")
    group.add_argument("--openai", action="store_true", help="Switch to OpenAI preset")
    group.add_argument("--anthropic", action="store_true", help="Switch to Anthropic preset")
    group.add_argument("--current", action="store_true", help="Show current config")
    group.add_argument("--restore", action="store_true", help="Restore from backup")
    group.add_argument("--test", action="store_true", help="Test API connectivity")

    args = parser.parse_args()

    if args.deepseek:
        switch_to_provider("deepseek")
    elif args.deepseek_pro:
        switch_to_provider("deepseek-pro")
    elif args.openai:
        switch_to_provider("openai")
    elif args.anthropic:
        switch_to_provider("anthropic")
    elif args.current:
        show_current()
    elif args.restore:
        restore_backup()
    elif args.test:
        test_api_connection()


if __name__ == "__main__":
    main()
