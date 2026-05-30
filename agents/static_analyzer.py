import os
import time
import logging
import json
import docker
from typing import Callable, Any
from utils.github_api import SafeGitHubSession
from events import BountyVerifiedEvent

logger = logging.getLogger(__name__)

class StaticAnalyzer:
    """
    Proactively hunts for vulnerabilities in random popular repositories using Semgrep.
    """
    def __init__(self, publish_event: Callable[[Any], None]):
        self.publish_event = publish_event
        self.workspace_root = os.path.join(os.getcwd(), "workspaces")
        os.makedirs(self.workspace_root, exist_ok=True)
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"StaticAnalyzer: Docker disabled. {e}")
            self.docker_client = None

    def get_session(self):
        return SafeGitHubSession()

    def scan(self):
        if not self.docker_client or not self.github_token:
            return

        logger.info("StaticAnalyzer: Searching for a popular repository to scan...")
        session = self.get_session()
        headers = {"Authorization": f"token {self.github_token}", "Accept": "application/vnd.github.v3+json"}
        
        try:
            # Find a recently updated repo with decent stars
            res = session.get("https://api.github.com/search/repositories", params={"q": "stars:>500 pushed:>2026-05-25", "sort": "updated", "per_page": 5}, headers=headers)
            if res.status_code != 200:
                return
            
            repos = res.json().get("items", [])
            for repo in repos:
                repo_name = repo["full_name"]
                repo_path = os.path.join(self.workspace_root, repo_name.replace("/", "_") + "_sa")
                
                if os.path.exists(repo_path):
                    continue # Already scanned recently
                
                logger.info(f"StaticAnalyzer: Targeting {repo_name} for Semgrep analysis.")
                import git
                try:
                    git.Repo.clone_from(f"https://github.com/{repo_name}.git", repo_path, depth=1)
                except Exception as e:
                    logger.warning(f"StaticAnalyzer: Failed to clone {repo_name}: {e}")
                    continue
                
                # Run Semgrep
                logger.info(f"StaticAnalyzer: Running Semgrep on {repo_name}...")
                try:
                    output = self.docker_client.containers.run(
                        "returntocorp/semgrep",
                        command="semgrep scan --config auto --json /src",
                        volumes={repo_path: {'bind': '/src', 'mode': 'ro'}},
                        remove=True,
                        stdout=True,
                        stderr=False
                    )
                    
                    data = json.loads(output.decode("utf-8"))
                    results = data.get("results", [])
                    high_vulns = [r for r in results if r.get("extra", {}).get("severity") in ["ERROR", "WARNING"]]
                    
                    if high_vulns:
                        logger.info(f"StaticAnalyzer: Found {len(high_vulns)} vulnerabilities in {repo_name}!")
                        # Take the first significant one
                        vuln = high_vulns[0]
                        msg = vuln.get("extra", {}).get("message", "Security vulnerability")
                        path = vuln.get("path", "")
                        lines = vuln.get("extra", {}).get("lines", "")
                        
                        issue_body = f"Semgrep identified a vulnerability in `{path}`:\n\n```\n{lines}\n```\n\nDetails: {msg}"
                        
                        payload = {
                            "repo": repo_name,
                            "issue_title": f"Security Patch: Fix vulnerability in {path}",
                            "issue_body": issue_body,
                            "issue_number": "AUTO",
                            "issue_url": f"https://github.com/{repo_name}/security",
                            "workspace_path": repo_path
                        }
                        
                        # Emit BOUNTY_VERIFIED so PREngineer picks it up
                        self.publish_event(BountyVerifiedEvent(payload=payload))
                        break # Only trigger one per cycle to avoid overload
                        
                except Exception as e:
                    logger.warning(f"StaticAnalyzer: Semgrep failed on {repo_name}: {e}")

        except Exception as e:
            logger.error(f"StaticAnalyzer: Scan failed: {e}")
