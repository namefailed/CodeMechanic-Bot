import os
import time
import shutil
import logging
import json
import datetime
import docker
from typing import Callable, Any
from utils.github_api import SafeGitHubSession
from events import BountyVerifiedEvent

logger = logging.getLogger(__name__)

class StaticAnalyzer:
    """
    Proactively hunts for vulnerabilities in random popular repositories using Semgrep, Trivy, and Gitleaks.
    """
    def __init__(self, publish_event: Callable[[Any], None], bounty_active_event=None):
        self.publish_event = publish_event
        self.bounty_active_event = bounty_active_event
        self.workspace_root = os.path.join(os.getcwd(), "workspaces")
        os.makedirs(self.workspace_root, exist_ok=True)
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        self._docker_client = None

    @property
    def docker_client(self):
        try:
            if not self._docker_client:
                self._docker_client = docker.from_env()
            else:
                self._docker_client.ping()
            return self._docker_client
        except Exception as e:
            logger.warning(f"StaticAnalyzer: Docker disabled or disconnected. {e}")
            self._docker_client = None
            return None

    def get_session(self):
        return SafeGitHubSession()

    def _run_semgrep(self, repo_path, repo_name):
        logger.info(f"StaticAnalyzer: Running Semgrep on {repo_name}...")
        try:
            output = self.docker_client.containers.run(
                "returntocorp/semgrep:latest",
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
                vuln = high_vulns[0]
                msg = vuln.get("extra", {}).get("message", "Security vulnerability")
                path = vuln.get("path", "")
                lines = vuln.get("extra", {}).get("lines", "")
                
                issue_body = f"Semgrep identified a vulnerability in `{path}`:\n\n```\n{lines}\n```\n\nDetails: {msg}"
                return {
                    "repo": repo_name,
                    "issue_title": f"Security Patch: Fix vulnerability in {path}",
                    "issue_body": issue_body,
                    "issue_number": "AUTO_SEMGREP",
                    "issue_url": f"https://github.com/{repo_name}/security",
                    "workspace_path": repo_path
                }
        except Exception as e:
            logger.warning(f"StaticAnalyzer: Semgrep failed on {repo_name}: {e}")
        return None

    def _run_trivy(self, repo_path, repo_name):
        logger.info(f"StaticAnalyzer: Running Trivy on {repo_name}...")
        try:
            output = self.docker_client.containers.run(
                "aquasec/trivy:latest",
                command="fs --scanners vuln,misconfig --format json /src",
                volumes={repo_path: {'bind': '/src', 'mode': 'ro'}},
                remove=True,
                stdout=True,
                stderr=False
            )
            data = json.loads(output.decode("utf-8"))
            results = data.get("Results", [])
            for res in results:
                vulns = res.get("Vulnerabilities", [])
                if vulns:
                    # Find high/critical
                    criticals = [v for v in vulns if v.get("Severity") in ["CRITICAL", "HIGH"]]
                    if criticals:
                        vuln = criticals[0]
                        pkg_name = vuln.get("PkgName", "Unknown")
                        vuln_id = vuln.get("VulnerabilityID", "Unknown")
                        title = vuln.get("Title", "Vulnerability")
                        desc = vuln.get("Description", "No description provided.")
                        target = res.get("Target", "Unknown")
                        
                        issue_body = f"Trivy identified a {vuln.get('Severity')} vulnerability in `{target}` regarding `{pkg_name}` ({vuln_id}):\n\n{desc}\n\nTitle: {title}"
                        return {
                            "repo": repo_name,
                            "issue_title": f"Security Patch: Fix {vuln_id} in {pkg_name}",
                            "issue_body": issue_body,
                            "issue_number": "AUTO_TRIVY",
                            "issue_url": f"https://github.com/{repo_name}/security",
                            "workspace_path": repo_path
                        }
        except Exception as e:
            logger.warning(f"StaticAnalyzer: Trivy failed on {repo_name}: {e}")
        return None

    def _run_gitleaks(self, repo_path, repo_name):
        logger.info(f"StaticAnalyzer: Running Gitleaks on {repo_name}...")
        try:
            # Gitleaks returns exit code 1 if leaks are found, causing docker.errors.ContainerError
            # We catch it and read the output.
            output = ""
            try:
                output = self.docker_client.containers.run(
                    "zricethezav/gitleaks:latest",
                    command="detect --source /src --no-git --report-format json",
                    volumes={repo_path: {'bind': '/src', 'mode': 'ro'}},
                    remove=True,
                    stdout=True,
                    stderr=False
                )
            except docker.errors.ContainerError as ce:
                output = ce.stdout
            
            # gitleaks outputs JSON directly to stdout if report-format is json and no report-path is provided
            if output:
                data = json.loads(output.decode("utf-8"))
                if len(data) > 0:
                    leak = data[0]
                    file = leak.get("File", "Unknown")
                    rule = leak.get("Description", "Secret Leak")
                    
                    # LOG IT INSTEAD OF SUBMITTING A PR
                    logger.error(f"🚨 CRITICAL ALERT: Gitleaks found a leaked secret in {repo_name} -> {file} ({rule}) 🚨")
                    
                    # You could optionally save it to DB for manual review here.
                    
                    return {
                        "is_secret": True,
                        "repo": repo_name,
                        "file": file,
                        "rule": rule
                    }
        except Exception as e:
            logger.warning(f"StaticAnalyzer: Gitleaks failed on {repo_name}: {e}")
        return None

    def scan(self):
        if not self.docker_client or not self.github_token:
            return

        logger.info("StaticAnalyzer: Searching for a popular repository to scan...")
        session = self.get_session()
        headers = {"Authorization": f"token {self.github_token}", "Accept": "application/vnd.github.v3+json"}
        
        try:
            # Rolling 30-day window of recently-pushed popular repos (was a hardcoded date).
            recent = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            res = session.get("https://api.github.com/search/repositories", params={"q": f"stars:>500 pushed:>{recent}", "sort": "updated", "per_page": 5}, headers=headers)
            if res.status_code != 200:
                return
            
            repos = res.json().get("items", [])
            for repo in repos:
                # Check synchronization flag!
                if self.bounty_active_event and self.bounty_active_event.is_set():
                    logger.info("StaticAnalyzer: Bounty scan is active. Pausing researcher...")
                    return

                repo_name = repo["full_name"]
                repo_path = os.path.join(self.workspace_root, repo_name.replace("/", "_") + "_sa")

                # Start from a clean slate each cycle so old clones don't accumulate.
                if os.path.exists(repo_path):
                    shutil.rmtree(repo_path, ignore_errors=True)

                logger.info(f"StaticAnalyzer: Targeting {repo_name} for Security analysis.")
                import git
                try:
                    git.Repo.clone_from(f"https://github.com/{repo_name}.git", repo_path, depth=1)
                except Exception as e:
                    logger.warning(f"StaticAnalyzer: Failed to clone {repo_name}: {e}")
                    continue

                try:
                    # 1. Semgrep
                    payload = self._run_semgrep(repo_path, repo_name)

                    # 2. Trivy (if Semgrep didn't find anything)
                    if not payload:
                        payload = self._run_trivy(repo_path, repo_name)

                    # 3. Gitleaks
                    secret_leak = self._run_gitleaks(repo_path, repo_name)
                    if secret_leak:
                        logger.warning(f"StaticAnalyzer: Found leaked secret in {repo_name}. Manual review required.")
                        # We don't automatically generate PRs for secrets to prevent exposing them in forks.

                    if payload:
                        logger.info(f"StaticAnalyzer: Found vulnerability in {repo_name}! Sending to PREngineer.")
                        self.publish_event(BountyVerifiedEvent(payload=payload))
                        break  # One per cycle
                finally:
                    # Don't let scanned clones pile up on disk.
                    shutil.rmtree(repo_path, ignore_errors=True)

        except Exception as e:
            logger.error(f"StaticAnalyzer: Scan failed: {e}")
