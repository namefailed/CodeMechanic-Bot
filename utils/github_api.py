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
        response = super().request(method, url, *args, **kwargs)
        
        # Check GitHub rate limit headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining and int(remaining) <= 2:
            reset_timestamp = response.headers.get("X-RateLimit-Reset")
            if reset_timestamp:
                reset_time = int(reset_timestamp)
                sleep_duration = max(0, reset_time - int(time.time())) + 5
                logger.warning(f"GitHub Rate Limit extremely low! Sleeping for {sleep_duration} seconds until reset...")
                time.sleep(sleep_duration)
                logger.info("Awake! Rate limit should be reset now.")
                
        return response
