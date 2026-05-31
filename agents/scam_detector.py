"""
Scam Detector Agent
Applies strict heuristics to filter out fake or unprofitable bug bounties.
Emits 'BOUNTY_VERIFIED' for legitimate targets, and 'SCAM_DETECTED' for bad ones.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
import os
import logging
from events import BountyVerifiedEvent, ScamDetectedEvent
from utils.github_api import SafeGitHubSession
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScamDetector:
    """
    Agent responsible for identifying and filtering out scam repositories 
    that harvest free labor but never merge PRs.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the ScamDetector.
        
        Args:
            publish_event: Callback function to emit events to the orchestrator.
        """
        self.publish_event = publish_event
        self.blacklist = ["SecureBananaLabs", "ClankerNation"]
        self.timeout = 30  # Network timeout in seconds
        self.eval_cache = {}  # Cache to prevent duplicate checks per repo

    def evaluate(self, payload: dict):
        """
        Evaluates a repository based on strict heuristics (stars, open issues, merged PRs).
        
        Args:
            payload: Dictionary containing 'repo' and other bounty details.
        """
        repo_name = payload.get('repo')
        
        if not repo_name:
            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "No repo name provided"}))
            return
            
        if repo_name in self.eval_cache:
            result = self.eval_cache[repo_name]
            if result == "PASS":
                self.publish_event(BountyVerifiedEvent(payload=payload))
            else:
                self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": result}))
            return

        logger.info(f"ScamDetector: Evaluating repo {repo_name}...")
        owner = repo_name.split("/")[0]
        if owner in self.blacklist:
            logger.warning(f"ScamDetector: {repo_name} rejected - Owner is blacklisted.")
            self.eval_cache[repo_name] = "Blacklisted owner"
            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "Blacklisted owner"}))
            return

        # "bounty" in the repo name is a huge red flag (often a honeypot)
        if "bounty" in repo_name.lower():
            logger.warning(f"ScamDetector: {repo_name} rejected - Contains 'bounty' in repo name.")
            self.eval_cache[repo_name] = "'bounty' in repo name"
            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "'bounty' in repo name"}))
            return

        session = SafeGitHubSession()

        try:
            # 1. Check repository statistics
            repo_url = f"https://api.github.com/repos/{repo_name}"
            response = session.get(repo_url, timeout=self.timeout)
            response.raise_for_status()
            repo_data = response.json()

            # Reject repositories with less than 3 stars
            stars = repo_data.get("stargazers_count", 0)
            if stars < 3:
                logger.warning(f"ScamDetector: {repo_name} rejected - Too few stars ({stars}).")
                self.eval_cache[repo_name] = "Too few stars"
                self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "Too few stars"}))
                return

            # Dead Repo Detection
            pushed_at_str = repo_data.get("pushed_at")
            if pushed_at_str:
                pushed_at_date = datetime.datetime.strptime(pushed_at_str, "%Y-%m-%dT%H:%M:%SZ")
                days_since_push = (datetime.datetime.utcnow() - pushed_at_date).days
                if days_since_push > 180:
                    logger.warning(f"ScamDetector: {repo_name} rejected - Dead repo (last push {days_since_push} days ago).")
                    self.eval_cache[repo_name] = "Dead repo"
                    self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "Dead repo"}))
                    return

            # Reject repositories flooded with open issues
            open_issues = repo_data.get("open_issues_count", 0)
            if open_issues > 60:
                logger.warning(f"ScamDetector: {repo_name} rejected - Too many open issues ({open_issues}).")
                self.eval_cache[repo_name] = "Too many open issues"
                self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "Too many open issues"}))
                return

            # 2. Check for merged PR history
            # A repository that has never merged a PR is likely a scam or inactive
            pulls_url = f"https://api.github.com/repos/{repo_name}/pulls?state=closed&per_page=100"
            pulls_response = session.get(pulls_url, timeout=self.timeout)
            pulls_response.raise_for_status()
            pulls_data = pulls_response.json()
            
            merged_prs = sum(1 for pr in pulls_data if pr.get("merged_at") is not None)
            if merged_prs == 0:
                logger.warning(f"ScamDetector: {repo_name} rejected - 0 merged PRs found.")
                self.eval_cache[repo_name] = "0 merged PRs"
                self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "0 merged PRs"}))
                return

            # 3. Check if issue is already claimed in comments
            issue_number = payload.get("issue_number")
            if issue_number:
                comments_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
                comments_res = session.get(comments_url, timeout=self.timeout)
                if comments_res.status_code == 200:
                    for comment in comments_res.json():
                        body = comment.get("body", "").lower()
                        # Simple heuristics to detect if someone claimed it
                        if any(phrase in body for phrase in ["working on this", "will submit a pr", "i'll take this", "i am working on", "i can do this"]):
                            logger.warning(f"ScamDetector: {repo_name}#{issue_number} rejected - Already claimed in comments.")
                            self.eval_cache[repo_name] = "Already claimed in comments"
                            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": "Already claimed in comments"}))
                            return

            logger.info(f"ScamDetector: {repo_name} passed all heuristics!")
            self.eval_cache[repo_name] = "PASS"
            self.publish_event(BountyVerifiedEvent(payload=payload))

        except requests.exceptions.RequestException as e:
            if getattr(e.response, "status_code", None) == 404:
                reason = "Repository or Pulls endpoint not found (404)"
                logger.warning(f"ScamDetector: {repo_name} rejected - {reason}")
            else:
                reason = f"Network Error: {e}"
                logger.error(f"ScamDetector: Network error evaluating {repo_name}: {e}")
            self.eval_cache[repo_name] = reason
            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": reason}))
        except Exception as e:
            logger.error(f"ScamDetector: Unexpected error evaluating {repo_name}: {e}")
            self.eval_cache[repo_name] = f"Unexpected Error: {e}"
            self.publish_event(ScamDetectedEvent(payload={"repo": repo_name, "reason": f"Unexpected Error: {e}"}))
