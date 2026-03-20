#!/usr/bin/env python3
"""Standalone test for Ollama service - bypasses ROS2 dependencies"""

import httpx


def test_ollama():
    print("=" * 50)
    print("Ollama Service Test")
    print("=" * 50)

    host = "localhost"
    port = 11434
    model = "qwen3.5:9b"

    # Create client without proxy
    no_proxy_client = httpx.Client(
        timeout=30.0, proxies={"http://": None, "https://": None}
    )

    # 1. Check service status
    print("\n[1] Checking Ollama service status...")
    try:
        response = no_proxy_client.get(f"http://{host}:{port}")
        print(f"    ✓ Service is running: {response.text}")
    except Exception as e:
        print(f"    ✗ Failed to connect: {e}")
        return False

    # 2. Check available models
    print("\n[2] Checking available models...")
    try:
        response = no_proxy_client.get(f"http://{host}:{port}/api/tags")
        models = response.json().get("models", [])
        print(f"    Found {len(models)} model(s):")
        for m in models:
            print(f"      - {m['name']} ({m.get('size', 'N/A')} bytes)")
    except Exception as e:
        print(f"    ✗ Failed to list models: {e}")
        return False

    # 3. Test inference with the model
    print(f"\n[3] Testing inference with {model}...")
    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Say 'Hello, robot!' in exactly 3 words."}
            ],
            "stream": False,
        }
        response = no_proxy_client.post(f"http://{host}:{port}/api/chat", json=payload)
        result = response.json()
        content = result.get("message", {}).get("content", "")
        print(f"    ✓ Model responded: {content}")
    except Exception as e:
        print(f"    ✗ Inference failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("All tests PASSED! ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    import sys

    success = test_ollama()
    sys.exit(0 if success else 1)
