import requests
import json
import sys
import os
from dotenv import load_dotenv

def test_connection():
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
        print(f"Loading env from {env_file}")
        load_dotenv(env_file, override=True)
    else:
        print("No env file provided, using existing env vars or defaults")

    api_key = os.getenv("ARK_API_KEY")
    base_url = os.getenv("ARK_BASE_URL")
    model = os.getenv("LLM_MODEL", "doubao-seed-1-6-flash-250828")

    if not api_key:
        print("Error: ARK_API_KEY not found")
        return
    if not base_url:
        print("Error: ARK_BASE_URL not found")
        return

    print(f"Raw ARK_BASE_URL: {base_url}")

    # Logic from app/services/llm.py
    raw_url = base_url.strip().strip('"').strip("'")
    if not raw_url.startswith("http"):
            raw_url = f"https://{raw_url}"
            
    url = raw_url.rstrip('/')
    if not url.endswith('/responses'):
            url = f"{url}/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Hello, are you working?"
                    }
                ]
            }
        ],
        "stream": True
    }

    print(f"Testing URL: {url}")
    print(f"Model: {model}")
    print("Sending request...")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print("-" * 20)
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
        print("-" * 20)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
