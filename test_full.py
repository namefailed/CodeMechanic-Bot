import time
import requests
import sys
from orchestrator import Orchestrator

def verify_ollama():
    print("Verifying Ollama and gemma4:e4b...")
    for i in range(300): # Wait up to 5 minutes
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gemma4:e4b",
                    "prompt": "Say 'hello world'",
                    "stream": False
                },
                timeout=10
            )
            if response.status_code == 200:
                print("Success! Ollama is responding locally with gemma4:e4b.")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Only print every 10 seconds to avoid spamming logs
        if i % 10 == 0:
            print(f"Waiting for gemma4:e4b to finish pulling... (Attempt {i+1}/300)")
        time.sleep(1)
        
    print("Failed to verify Ollama model after 5 minutes.")
    return False

def run_end_to_end():
    if not verify_ollama():
        sys.exit(1)
        
    print("\n--- Starting Full End-to-End Orchestrator Pipeline Test ---\n")
    bot = Orchestrator()
    
    # Mock payload to bypass radar polling
    mock_payload = {
        "repo": "octocat/Hello-World",
        "issue_title": "Update README.md to say Hello to Antigravity!",
        "issue_url": "https://github.com/octocat/Hello-World/issues/1",
        "comments": 0
    }
    
    print("Triggering the ScamDetector (Step 2)...")
    # Fire it directly into ScamDetector to start the chain
    bot.scam_detector.evaluate(mock_payload)

if __name__ == "__main__":
    run_end_to_end()
