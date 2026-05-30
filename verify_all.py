import time
import requests
import sys

def verify():
    print("Verifying Ollama and Gemma3:4b...")
    # Wait for Ollama model to be available
    for i in range(300): # Wait up to 5 minutes
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gemma3:4b",
                    "prompt": "Say 'hello world'",
                    "stream": False
                },
                timeout=10
            )
            if response.status_code == 200:
                print("Success! Ollama is responding locally with gemma3:4b.")
                print("Response:", response.json().get("response"))
                return
        except requests.exceptions.RequestException:
            pass
        
        # Only print every 10 seconds to avoid spamming logs
        if i % 10 == 0:
            print(f"Waiting for gemma3:4b... (Attempt {i+1}/300)")
        time.sleep(1)
        
    print("Failed to verify Ollama model after 5 minutes.")
    sys.exit(1)

if __name__ == "__main__":
    verify()
