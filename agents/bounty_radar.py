"""
Bounty Radar Agent
Scans GitHub for open bounties across multiple platforms (generic bounties, Algora, Polar).
Emits 'BOUNTY_FOUND' events when a new bounty matches our criteria.
"""

import requests
import datetime
import os
import logging
from events import BountyFoundEvent
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BountyRadar:
    """
    Agent responsible for finding new bug bounty opportunities.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the BountyRadar.
        
        Args:
            publish_event: Callback function to emit events to the orchestrator.
        """
        self.publish_event = publish_event
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        self.timeout = 30  # Network timeout in seconds

    def scan(self):
        """
        Executes a scan against the GitHub API for bounties.
        Finds 'Speed Game' (new) and 'Patience Harvest' (abandoned) bounties.
        """
        logger.info("BountyRadar: Scanning GitHub for bounties...")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        else:
            logger.warning("BountyRadar: GITHUB_TOKEN not set. Rate limits will be severely restricted.")

        now = datetime.datetime.utcnow()
        two_days_ago = (now - datetime.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        fourteen_days_ago = (now - datetime.timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Queries combining multiple sources:
        # - label:bounty (Generic)
        # - label:algora (Algora.io bounties)
        # - label:polar (Polar.sh bounties)
        queries = [
            # The Speed Game: New bounties (< 48 hours)
            f'is:issue is:open label:bounty created:>={two_days_ago}',
            f'is:issue is:open label:algora created:>={two_days_ago}',
            f'is:issue is:open label:polar created:>={two_days_ago}',
            
            # The Patience Harvest: Abandoned claims (> 14 days old)
            f'is:issue is:open label:bounty updated:<={fourteen_days_ago}',
            f'is:issue is:open label:algora updated:<={fourteen_days_ago}',
            f'is:issue is:open label:polar updated:<={fourteen_days_ago}',
            
            # General fallback for good first issues
            f'"good first issue" bounty is:issue is:open created:>={two_days_ago}'
        ]

        found_issues = set()

        for query in queries:
            try:
                url = f'https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30'
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                logger.info(f"BountyRadar: Found {len(items)} issues for query: {query}")

                for item in items:
                    issue_url = item.get("html_url")
                    if issue_url in found_issues:
                        continue
                    found_issues.add(issue_url)

                    comments = item.get("comments", 0)
                    is_patience = 'updated:<=' in query
                    
                    # Competition filters
                    if not is_patience and comments > 3:
                        # Too much competition for a new bounty
                        continue
                    
                    if is_patience and comments > 15:
                        # Too crowded even for patience harvest
                        continue

                    repo_url = item.get("repository_url", "")
                    repo_name = repo_url.replace("https://api.github.com/repos/", "")
                    
                    payload = {
                        "issue_title": item.get("title"),
                        "issue_url": issue_url,
                        "issue_number": item.get("number"),
                        "repo": repo_name,
                        "comments": comments,
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at"),
                        "strategy": "patience_harvest" if is_patience else "speed_game"
                    }
                    
                    # Emit event to pass the bounty to the ScamDetector
                    self.publish_event(BountyFoundEvent(payload=payload))

            except requests.exceptions.RequestException as e:
                logger.error(f"BountyRadar: Network error scanning GitHub with query '{query}': {e}")
            except Exception as e:
                logger.error(f"BountyRadar: Unexpected error scanning GitHub: {e}")
