#!/usr/bin/env python3
"""Test script to see the actual Perplexity API response structure."""

import asyncio
import aiohttp
import json
from src.config.loader import config_loader


async def test_perplexity_response():
    """Test Perplexity API and show the actual response structure."""
    
    api_key = config_loader.get_env("PERPLEXITY_API_KEY")
    if not api_key or api_key == "your_perplexity_api_key":
        print("❌ PERPLEXITY_API_KEY not configured")
        return
    
    url = "https://api.perplexity.ai/chat/completions"
    
    # Create search prompt for Perplexity
    search_prompt = """Search for information about: Latest AI developments 2024 machine learning breakthroughs

Please provide comprehensive search results with multiple sources. For each source, include:
1. Title of the content
2. URL/source link
3. Relevant excerpt or summary
4. Key information related to the query

Focus on recent, authoritative sources and provide diverse perspectives."""

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a search assistant. Provide comprehensive search results with sources, titles, and relevant content excerpts."
            },
            {
                "role": "user", 
                "content": search_prompt
            }
        ],
        "max_tokens": 4000,
        "temperature": 0.2,
        "return_citations": True,
        "return_images": False
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Making Perplexity API call...")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("✅ API call successful!")
                    print(f"📊 Response keys: {list(data.keys())}")
                    
                    # Pretty print the full response
                    print("\n📄 FULL RESPONSE:")
                    print(json.dumps(data, indent=2))
                    
                    # Analyze the structure
                    print("\n🔍 RESPONSE ANALYSIS:")
                    
                    if 'choices' in data:
                        print(f"Choices: {len(data['choices'])}")
                        if data['choices']:
                            choice = data['choices'][0]
                            print(f"Choice keys: {list(choice.keys())}")
                            
                            if 'message' in choice:
                                message = choice['message']
                                print(f"Message keys: {list(message.keys())}")
                                print(f"Content length: {len(message.get('content', ''))}")
                                print(f"Content preview: {message.get('content', '')[:200]}...")
                    
                    if 'citations' in data:
                        print(f"Citations: {len(data['citations'])}")
                        for i, citation in enumerate(data['citations'][:3]):
                            print(f"  Citation {i+1}: {list(citation.keys())}")
                    else:
                        print("No citations in response")
                    
                    if 'usage' in data:
                        print(f"Usage: {data['usage']}")
                        
                else:
                    error_text = await response.text()
                    print(f"❌ API error: {response.status}")
                    print(f"Error response: {error_text}")
                    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        print(f"Exception type: {type(e).__name__}")


if __name__ == "__main__":
    asyncio.run(test_perplexity_response())