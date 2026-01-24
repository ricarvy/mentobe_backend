import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load from .env.prod manually if needed, but for this test we'll use hardcoded values from the file we just read
# to verify EXACTLY what is being used.

API_KEY = "24bcf30d-06df-40f3-915f-fa045b16acd7"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-1-6-flash-250828"

async def test_llm():
    print(f"Testing Volcengine Ark Connection...")
    print(f"URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"Key: {API_KEY[:5]}...{API_KEY[-5:]}")
    
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "Hello, are you working?"}
            ],
        )
        print("✅ Success!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
