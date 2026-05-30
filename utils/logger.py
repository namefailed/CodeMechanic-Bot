import json
import os
import time
import logging

def log_ollama_activity(agent: str, prompt: str, response: str):
    activity_file = os.path.join(os.getcwd(), "ollama_activity.json")
    try:
        activities = []
        if os.path.exists(activity_file):
            with open(activity_file, "r", encoding="utf-8") as f:
                try: 
                    activities = json.load(f)
                except: 
                    pass
        
        activities.append({
            "timestamp": time.time(),
            "agent": agent,
            "prompt": prompt,
            "response": response
        })
        
        # Keep last 50 activities to prevent huge file
        activities = activities[-50:]
        
        with open(activity_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to log Ollama activity: {e}")
