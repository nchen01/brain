#!/usr/bin/env python3
"""Test script to check available Perplexity models."""

import asyncio
import aiohttp
import os
from src.config.loader import config_loader


async def test_perplexity_models():
    """Test different Perplexity models to find the correct one."""
    
    api_key = config_loader.get_env("PERPLEXITY_API_KEY")
    if not api_key or api_key == "your_perplexity_api_key":
        print("❌ PERPLEXITY_API_KEY not configured")
        return
    
    print("🔑 API Key configured")
    
    # Common Perplexity model names to try
    models_to_try = [
        "llama-3.1-sonar-small-128k-online",
        "llama-3.1-sonar-large-128k-online", 
        "sonar-small-online",
        "sonar-medium-online",
        "sonar-large-online",
        "sonar",
        "sonar-base",
        "llama-3.1-sonar-small-128k-chat",
        "llama-3.1-sonar-large-128k-chat"
    ]
    
    url = "https://api.perplexity.ai/chat/completions"
    
    for model in models_to_try:
        print(f"\n🧪 Testing model: {model}")
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user", 
                    "content": "What is AI? Give a very brief answer."
                }
            ],
            "max_tokens": 100,
            "temperature": 0.2
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        print(f"✅ SUCCESS: {model}")
                        print(f"   Response: {content[:100]}...")
                        
                        # Check if it has citations (online model)
                        if 'citations' in data:
                            print(f"   📚 Citations available: {len(data['citations'])}")
                        else:
                            print(f"   📚 No citations (offline model)")
                        
                        return model  # Return the first working model
                    else:
                        error_text = await response.text()
                        print(f"❌ FAILED: {response.status} - {error_text[:200]}...")
                        
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print("\n❌ No working models found")
    return None


if __name__ == "__main__":
    working_model = asyncio.run(test_perplexity_models())
    if working_model:
        print(f"\n🎉 Recommended model: {working_model}")
    else:
        print("\n💡 Check Perplexity documentation for current model names")