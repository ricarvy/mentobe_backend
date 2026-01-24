import asyncio
import os
import sys
from openai import AsyncOpenAI
from dotenv import load_dotenv

async def test_llm():
    # Allow loading specific env file if provided as argument
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
        print(f"Loading environment from {env_file}...")
        load_dotenv(env_file, override=True)
    
    # Get config from environment (or loaded .env file)
    api_key = os.getenv("ARK_API_KEY")
    base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    model = os.getenv("LLM_MODEL", "doubao-seed-1-6-flash-250828")

    print(f"Testing Volcengine Ark Connection...")
    print(f"URL: {base_url}")
    print(f"Model: {model}")
    print(f"Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ Error: ARK_API_KEY not found in environment")
        return

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    try:
        print("Sending request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello! Are you working?"}
            ],
        )
        print("✅ Success!")
        print("-" * 20)
        print(response.choices[0].message.content)
        print("-" * 20)
    except Exception as e:
        print(f"❌ Failed: {e}")
        # Print more details if available
        if hasattr(e, 'response'):
             print(f"Status Code: {e.status_code}")
             print(f"Response Body: {e.response}")

if __name__ == "__main__":
    asyncio.run(test_llm())
