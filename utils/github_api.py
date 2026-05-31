import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
import os

logger = logging.getLogger(__name__)

class SafeGitHubSession(requests.Session):
    """
    A requests.Session wrapper that intercepts GitHub API responses 
    and automatically sleeps if the rate limit is hit.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        retry = Retry(connect=3, read=3, status=3, status_forcelist=[500, 502, 503, 504], backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        self.mount('http://', adapter)
        self.mount('https://', adapter)
        
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            self.headers.update({
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            })

    def request(self, method, url, *args, **kwargs):
        while True:
            response = super().request(method, url, *args, **kwargs)
            
            # Check secondary rate limit (Abuse Limits)
            if response.status_code in (403, 429) and "Retry-After" in response.headers:
                sleep_duration = int(response.headers.get("Retry-After")) + 1
                logger.warning(f"GitHub Secondary Rate Limit hit! Sleeping for {sleep_duration}s...")
                time.sleep(sleep_duration)
                continue  # Retry the request
                
            # Check primary rate limit
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining and int(remaining) == 0:
                reset_timestamp = response.headers.get("X-RateLimit-Reset")
                if reset_timestamp:
                    reset_time = int(reset_timestamp)
                    sleep_duration = max(0, reset_time - int(time.time())) + 5
                    logger.warning(f"GitHub Primary Rate Limit hit! Sleeping for {sleep_duration}s...")
                    time.sleep(sleep_duration)
                    continue  # Retry the request
            elif remaining and int(remaining) <= 2:
                reset_timestamp = response.headers.get("X-RateLimit-Reset")
                if reset_timestamp:
                    reset_time = int(reset_timestamp)
                    sleep_duration = max(0, reset_time - int(time.time())) + 5
                    logger.warning(f"GitHub Rate Limit extremely low! Sleeping for {sleep_duration}s before returning...")
                    time.sleep(sleep_duration)
                    # Do not retry; the request actually succeeded, we just want to throttle future requests
                    
            return response
