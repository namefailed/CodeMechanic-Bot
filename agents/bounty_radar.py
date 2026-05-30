"""
Bounty Radar Agent
Scans GitHub for open bounties across multiple platforms (generic bounties, Algora, Polar).
Emits 'BOUNTY_FOUND' events when a new bounty matches our criteria.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
import os
import logging
from events import BountyFoundEvent
from utils.github_api import SafeGitHubSession
from utils.database import Database
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
        self.timeout = 30  # Network timeout in seconds
        self.db = Database()
        self.github_user = None

    def _get_github_user(self):
        if not self.github_user:
            try:
                session = SafeGitHubSession()
                res = session.get("https://api.github.com/user", timeout=self.timeout)
                if res.status_code == 200:
                    self.github_user = res.json().get("login")
            except Exception as e:
                logger.warning(f"BountyRadar: Failed to fetch authenticated user: {e}")
        return self.github_user

    def scan(self):
        """
        Executes a scan against the GitHub API for bounties.
        Finds 'Speed Game' (new) and 'Patience Harvest' (abandoned) bounties.
        """
        logger.info("BountyRadar: Scanning GitHub for bounties...")
        logger.info("BountyRadar: Scanning GitHub for bounties...")

        now = datetime.datetime.utcnow()
        two_days_ago = (now - datetime.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        fourteen_days_ago = (now - datetime.timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Queries combining multiple sources:
        # - label:bounty (Generic)
        # - label:algora (Algora.io bounties)
        # - label:polar (Polar.sh bounties)
        # - label:gitcoin (Gitcoin bounties)
        # - label:"up-for-grabs" (Common OSS bounty label)
        queries = [
            # The Speed Game: New bounties (< 48 hours)
            f'is:issue is:open label:bounty created:>={two_days_ago}',
            f'is:issue is:open label:algora created:>={two_days_ago}',
            f'is:issue is:open label:polar created:>={two_days_ago}',
            
            # The Patience Harvest: Abandoned claims (> 14 days old)
            f'is:issue is:open label:bounty updated:<={fourteen_days_ago}',
            f'is:issue is:open label:algora updated:<={fourteen_days_ago}',
            f'is:issue is:open label:polar updated:<={fourteen_days_ago}',
            
            # 🚀 THE BIG NET (Broad Sweep): Catch everything with low competition
            'is:issue is:open label:bounty comments:<5',
            'is:issue is:open label:algora comments:<5',
            'is:issue is:open label:polar comments:<5',
            'is:issue is:open label:gitcoin comments:<5',
            'is:issue is:open label:"up-for-grabs" comments:<5',
            'is:issue is:open label:"bug-bounty" comments:<5',
            'is:issue is:open label:bounties comments:<5',
            'is:issue is:open label:paid comments:<5',
            'is:issue is:open "reward" label:"help wanted" comments:<5',
            'is:issue is:open "bounty" label:"help wanted" comments:<5',
            
            # General fallback for good first issues
            f'"good first issue" bounty is:issue is:open created:>={two_days_ago}'
        ]

        found_issues = set()
        session = SafeGitHubSession()

        for query in queries:
            try:
                url = f'https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30'
                response = session.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                logger.info(f"BountyRadar: Found {len(items)} issues for query: {query}")

                for item in items:
                    issue_url = item.get("html_url")
                    if issue_url in found_issues:
                        continue
                    
                    # Check database for deduplication
                    if self.db.get_status(issue_url):
                        continue
                        
                    found_issues.add(issue_url)

                    comments = item.get("comments", 0)
                    is_patience = 'updated:<=' in query
                    
                    # Competition filters
                    if item.get("assignee") or len(item.get("assignees", [])) > 0:
                        continue
                        
                    if not is_patience and comments > 3:
                        # Too much competition for a new bounty
                        continue
                    
                    if is_patience and comments > 15:
                        # Too crowded even for patience harvest
                        continue

                    repo_url = item.get("repository_url", "")
                    repo_name = repo_url.replace("https://api.github.com/repos/", "")
                    
                    # Do not target personal repositories
                    auth_user = self._get_github_user()
                    if auth_user and repo_name.lower().startswith(f"{auth_user.lower()}/"):
                        continue
                        
                    # Filter out RFCs and Proposals
                    issue_title_lower = item.get("title", "").lower()
                    if any(kw in issue_title_lower for kw in ["rfc", "proposal", "request for comments"]):
                        continue
                    
                    payload = {
                        "issue_title": item.get("title"),
                        "issue_body": item.get("body", ""),
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
