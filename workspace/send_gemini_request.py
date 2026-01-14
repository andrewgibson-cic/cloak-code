import json
import urllib.request
import os

def send_gemini_request():
    api_key = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": "Explain how AI works in one sentence."
            }]
        }]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode("utf-8")
            print(json.dumps(json.loads(result), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_gemini_request()
