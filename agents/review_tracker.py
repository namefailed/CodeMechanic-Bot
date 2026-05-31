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
from utils.github_api import SafeGitHubSession
from utils.database import Database

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
        self.db = Database()

    def track(self):
        """
        Polls the GitHub API for open PRs authored by the bot and, for any that have
        a formal "changes requested" review we haven't actioned yet, routes the
        feedback back to the PREngineer via a PR_REVIEWED event.
        """
        logger.info("ReviewTracker: Checking open PRs for change requests...")
        if not self.github_token:
            logger.warning("ReviewTracker: No GITHUB_TOKEN. Skipping tracking.")
            return

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.github_token}"
        }

        try:
            session = SafeGitHubSession()
            response = session.get(
                "https://api.github.com/search/issues",
                params={"q": "is:pr is:open author:@me"},
                headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            for item in response.json().get("items", []):
                pr_api = (item.get("pull_request") or {}).get("url")
                if not pr_api:
                    continue

                reviews_res = session.get(f"{pr_api}/reviews", headers=headers, timeout=self.timeout)
                if reviews_res.status_code != 200:
                    continue

                change_reviews = [r for r in reviews_res.json() if r.get("state") == "CHANGES_REQUESTED"]
                if not change_reviews:
                    continue

                latest = change_reviews[-1]
                review_key = f"review_{latest.get('id')}"
                if self.db.is_comment_processed(review_key):
                    continue
                self.db.mark_comment_processed(review_key)

                repo_name = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
                number = item.get("number")
                feedback = latest.get("body") or "The maintainer requested changes on this PR."

                logger.info(f"ReviewTracker: Change request on {repo_name} PR #{number}; routing to PREngineer.")
                self.publish_event(PRReviewedEvent(payload={
                    "repo": repo_name,
                    "issue_title": item.get("title"),
                    "issue_number": str(number),
                    "issue_url": item.get("html_url"),
                    "retry_count": 1,
                    "reviewer_feedback": f"Maintainer review: {feedback}",
                    "workspace_path": os.path.join(os.getcwd(), "workspaces", f"{repo_name.replace('/', '_')}_{number}"),
                }))

        except requests.exceptions.RequestException as e:
            logger.error(f"ReviewTracker: Network error fetching PRs: {e}")
        except Exception as e:
            logger.error(f"ReviewTracker: Unexpected error fetching PRs: {e}")
