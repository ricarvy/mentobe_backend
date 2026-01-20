from openai import AsyncOpenAI
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client for Volcengine Ark
# Note: api_key is passed dynamically to avoid issues with early initialization
# or missing env vars at module import time if not handled correctly.
# However, here we initialize it once. Ensure ARK_API_KEY is in .env

client = AsyncOpenAI(
    api_key=settings.ARK_API_KEY,
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

async def stream_tarot_interpretation(messages: list):
    """
    Stream tarot interpretation from LLM.
    
    Args:
        messages: List of message dicts [{"role": "user", "content": "..."}]
        
    Yields:
        str: Content chunks
    """
    try:
        # Re-check API key in case it was updated or missing at init
        if not client.api_key and settings.ARK_API_KEY:
            client.api_key = settings.ARK_API_KEY
            
        logger.info(f"Calling LLM model: {settings.LLM_MODEL}")
        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            stream=True,
            temperature=settings.LLM_TEMPERATURE,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        # In case of error, yield an error message so the client sees something
        yield f"\n[System Error: Failed to call AI service. Please try again later. Error: {str(e)}]"
