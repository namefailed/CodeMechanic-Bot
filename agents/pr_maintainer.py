import os
import logging
from typing import Callable, Any
from events import BaseEvent
from utils.github_api import SafeGitHubSession
from utils.database import Database

logger = logging.getLogger(__name__)

class MaintainerFeedbackEvent(BaseEvent):
    event_type = "MAINTAINER_FEEDBACK"

class PRMaintainer:
    """
    Monitors open Pull Requests authored by the bot.
    If a maintainer requests a change, it triggers PREngineer to fix it.
    """
    def __init__(self, publish_event: Callable[[Any], None]):
        self.publish_event = publish_event
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        self.db = Database()
        
    def get_session(self):
        return SafeGitHubSession()

    def check_prs(self):
        if not self.github_token:
            return
            
        logger.info("PRMaintainer: Checking for maintainer feedback on open PRs...")
        session = self.get_session()
        headers = {"Authorization": f"token {self.github_token}", "Accept": "application/vnd.github.v3+json"}
        
        try:
            # Get authenticated user login
            user_res = session.get("https://api.github.com/user", headers=headers)
            if user_res.status_code != 200:
                return
            login = user_res.json().get("login")
            
            # Search open PRs
            prs_res = session.get("https://api.github.com/search/issues", params={"q": f"author:{login} is:pr is:open"}, headers=headers)
            if prs_res.status_code != 200:
                return
                
            prs = prs_res.json().get("items", [])
            for pr in prs:
                comments_url = pr.get("comments_url")
                if not comments_url:
                    continue
                    
                comments_res = session.get(comments_url, headers=headers)
                if comments_res.status_code != 200:
                    continue
                    
                comments = comments_res.json()
                if not comments:
                    continue
                    
                # Look at the most recent comment
                last_comment = comments[-1]
                author = last_comment.get("user", {}).get("login")
                
                # If it's not us, treat as feedback
                if author != login:
                    comment_id = str(last_comment.get("id"))
                    pr_url = pr.get("html_url")
                    
                    # We need a way to track if we already responded. 
                    # For simplicity, if we haven't seen this comment ID, trigger an event.
                    # We can use the DB to store processed comments.
                    if self.db.is_comment_processed(comment_id):
                        continue
                        
                    self.db.mark_comment_processed(comment_id)
                    
                    repo_url = pr.get("repository_url")
                    repo_name = repo_url.replace("https://api.github.com/repos/", "")
                    
                    logger.info(f"PRMaintainer: Found new feedback on {repo_name} PR #{pr.get('number')} from {author}")
                    
                    payload = {
                        "repo": repo_name,
                        "issue_title": pr.get("title"),
                        "issue_number": str(pr.get("number")),
                        "issue_url": pr_url,
                        "retry_count": 1, # Triggers the retry logic in PREngineer
                        "reviewer_feedback": f"Maintainer {author} said: {last_comment.get('body')}",
                        "workspace_path": os.path.join(os.getcwd(), "workspaces", f"{repo_name.replace('/', '_')}_{pr.get('number')}"),
                        "is_maintainer_feedback": True
                    }
                    self.publish_event(MaintainerFeedbackEvent(payload=payload))

        except Exception as e:
            logger.error(f"PRMaintainer: Failed to check PRs: {e}")
