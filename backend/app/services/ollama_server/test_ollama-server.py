import requests
import json

# Your new ngrok URL
COLAB_URL = "URL"

def test_cloud_gpu():
    print(f"Testing connection to: {COLAB_URL} ...")
    
    # Endpoint for generating text
    url = f"{COLAB_URL}/api/generate"
    
    # Payload
    payload = {
        "model": "llama3",  # The model we pulled in Colab
        "prompt": "hi, is it working ?",
        "stream": False
    }

    try:
        # Send POST request
        response = requests.post(url, json=payload, timeout=30)
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            print("\n SUCCESS! The cloud GPU responded:")
            print("-" * 50)
            print(data.get("response"))
            print("-" * 50)
        else:
            print(f"\n Server Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\n Connection Failed: {e}")

if __name__ == "__main__":
    test_cloud_gpu()