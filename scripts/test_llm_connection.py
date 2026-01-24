import requests
import json
import sys

def test_connection():
    # Remove backticks if they were part of the copy-paste
    url = "https://ark.cn-beijing.volces.com/api/v3/responses"
    
    headers = {
        "Authorization": "Bearer 24bcf30d-06df-40f3-915f-fa045b16acd7",
        "Content-Type": "application/json"
    }
    
    # Cleaned up data structure from the curl command
    # Note: 'type': 'input_image' and 'input_text' seem specific to this endpoint/API version
    data = {
        "model": "doubao-seed-1-6-flash-250828",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
                    },
                    {
                        "type": "input_text",
                        "text": "你看见了什么？"
                    }
                ]
            }
        ]
    }

    print(f"Testing URL: {url}")
    print("Sending request...")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print("-" * 20)
        print("Response Body:")
        # Try to print pretty JSON if possible
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
        print("-" * 20)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
