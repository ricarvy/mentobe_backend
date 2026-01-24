import httpx
import json
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def stream_tarot_interpretation(messages: list):
    """
    Stream tarot interpretation from LLM using Volcengine /api/v3/responses endpoint.
    
    Args:
        messages: List of message dicts [{"role": "user", "content": "..."}]
        
    Yields:
        str: Content chunks
    """
    try:
        logger.info(f"Calling LLM model: {settings.LLM_MODEL} via {settings.ARK_BASE_URL}")
        
        # Transform OpenAI-style messages to Volcengine /responses input format
        # messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        # target input: [{"role": "system", "content": [{"type": "input_text", "text": "..."}]}, ...]
        
        volc_input = []
        for msg in messages:
            content_items = []
            if isinstance(msg["content"], str):
                content_items.append({"type": "input_text", "text": msg["content"]})
            elif isinstance(msg["content"], list):
                # Handle case where content is already a list (e.g. multimodal)
                # But here we assume we receive text primarily. 
                # If we need to support image here, we need to adapt.
                # For now, let's assume text.
                pass
            
            volc_input.append({
                "role": msg["role"],
                "content": content_items
            })

        # Ensure base URL ends with /responses (handle if user provided root or /responses)
        # settings.ARK_BASE_URL is typically "https://ark.cn-beijing.volces.com/api/v3"
        # Also handle potential quotes in env var or missing protocol
        raw_url = settings.ARK_BASE_URL.strip().strip('"').strip("'")
        if not raw_url.startswith("http"):
             raw_url = f"https://{raw_url}"
             
        url = raw_url.rstrip('/')
        if not url.endswith('/responses'):
             url = f"{url}/responses"

        headers = {
            "Authorization": f"Bearer {settings.ARK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.LLM_MODEL,
            "input": volc_input,
            "parameters": {
                "temperature": settings.LLM_TEMPERATURE
            },
            "stream": True # Try enabling stream
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"LLM API Error: {response.status_code} - {error_text.decode()}")
                    yield f"\n[System Error: AI service returned {response.status_code}.]"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        line = line[5:].strip()
                        if line == "[DONE]":
                            break
                        try:
                            data = json.loads(line)
                            # Check for output text in the response structure
                            # Structure might be: data.choices[0].delta.content or data.output[0].content...
                            # Based on /responses API, structure is different.
                            # Let's handle both OpenAI-compatible stream (if supported) and native stream
                            
                            # Native stream structure often has 'output' list
                            if "output" in data and isinstance(data["output"], list):
                                for item in data["output"]:
                                    if "content" in item:
                                        for content_part in item["content"]:
                                            if content_part.get("type") == "output_text":
                                                yield content_part.get("text", "")
                            
                            # Fallback/OpenAI style check
                            elif "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                                    
                        except json.JSONDecodeError:
                            continue
                            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        yield f"\n[System Error: Failed to call AI service. Please try again later. Error: {str(e)}]"
