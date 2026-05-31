"""
DevOps Monitor Agent
Tracks the status of CI/CD pipelines on submitted PRs to ensure the
automated fix didn't break existing tests.
"""

import logging
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DevOpsMonitor:
    """
    Agent responsible for monitoring GitHub Actions or other CI tools.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the DevOpsMonitor.
        
        Args:
            publish_event: Callback function to emit events.
        """
        self.publish_event = publish_event

    def track_ci(self, payload: dict):
        """
        Records that a PR was submitted so its CI/merge outcome can be observed.

        CI runs asynchronously after submission, so this handler does not block or
        fabricate a pass/fail result; the dashboard's PR poller tracks the real
        merge/close outcome over time.
        """
        repo_name = payload.get('repo')
        pr_ref = payload.get('pr_api_url') or payload.get('issue_url') or 'unknown PR'
        logger.info(f"DevOpsMonitor: {repo_name} PR submitted ({pr_ref}); CI/merge outcome will be tracked by the PR poller.")
