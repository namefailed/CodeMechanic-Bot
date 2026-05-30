"""
Review Tracker Agent
Monitors pull requests authored by the bot for maintainer feedback.
Emits 'PR_REVIEWED' events if maintainers request changes, allowing the bot
to iteratively fix issues autonomously.
"""

import os
import logging
import requests
from events import PRReviewedEvent
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReviewTracker:
    """
    Agent responsible for continuously checking the status of open PRs.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the ReviewTracker.
        
        Args:
            publish_event: Callback function to emit events to the orchestrator.
        """
        self.publish_event = publish_event
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        self.timeout = 30  # Network timeout in seconds

    def track(self):
        """
        Polls the GitHub API for PRs created by the authenticated user and
        checks if there are any new review comments requesting changes.
        """
        logger.info("ReviewTracker: Checking open PRs for feedback...")
        if not self.github_token:
            logger.warning("ReviewTracker: No GITHUB_TOKEN. Skipping tracking.")
            return

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.github_token}"
        }
        
        try:
            url = "https://api.github.com/search/issues?q=is:pr is:open author:@me"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            for item in items:
                pr_url = item.get("html_url")
                logger.info(f"ReviewTracker: Polling PR {pr_url} for maintainer comments...")
                
                # In a real implementation, we would query the specific PR's comments
                # and emit an event if there are unactioned requests for changes.
                # Example:
                # self.publish_event(PRReviewedEvent(payload={"pr_url": pr_url, "feedback": "Please fix X"}))
                
        except requests.exceptions.RequestException as e:
            logger.error(f"ReviewTracker: Network error fetching PRs: {e}")
        except Exception as e:
            logger.error(f"ReviewTracker: Unexpected error fetching PRs: {e}")
