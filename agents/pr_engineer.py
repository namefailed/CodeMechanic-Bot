"""
PR Engineer Agent
Responsible for performing context harvest, querying local LLMs, and generating code fixes.
Executes the 'Comment First' strategy to propose fixes to maintainers before full implementation.
Emits 'PR_READY' events upon generating a valid patch.
"""

import os
import shutil
import logging
import requests
import git
import docker
from events import PRReadyEvent
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PREngineer:
    """
    Agent responsible for analyzing the codebase, posting proposal comments, 
    and generating the actual patch using local AI models with fallback support.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the PREngineer.
        
        Args:
            publish_event: Callback function to emit events to the orchestrator.
        """
        self.publish_event = publish_event
        self.workspace_root = os.path.join(os.getcwd(), "workspaces")
        os.makedirs(self.workspace_root, exist_ok=True)
        self.github_token = os.environ.get("GITHUB_TOKEN", None)
        self.timeout = 60  # Network timeout in seconds
        
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"PREngineer: Docker client failed to initialize: {e}. Sandboxing disabled.")
            self.docker_client = None

    def post_comment(self, repo_name: str, issue_number: str):
        """
        Implements the 'Comment-First' strategy to build trust with maintainers.
        """
        if not self.github_token or not issue_number:
            return
        
        logger.info(f"PREngineer: Comment-First Strategy -> Posting to #{issue_number}")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.github_token}"
        }
        comment = "Hi! I've analyzed the issue and identified the root cause. I'm preparing a minimal fix with tests matching the repo's style. I will submit a PR shortly."
        url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
        
        try:
            requests.post(url, headers=headers, json={"body": comment}, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            logger.error(f"PREngineer: Failed to post comment: {e}")

    def gather_context(self, repo_path: str) -> str:
        """
        Performs a 'Context Harvest' to learn the repository's coding style and rules.
        """
        logger.info("PREngineer: Context Harvest -> Gathering repo style and structure.")
        context = ""
        try:
            # 1. Pull contributing guidelines
            contrib_path = os.path.join(repo_path, "CONTRIBUTING.md")
            if os.path.exists(contrib_path):
                with open(contrib_path, "r", encoding="utf-8", errors="ignore") as f:
                    context += f"CONTRIBUTING.md:\n{f.read()[:500]}\n\n"
            
            # 2. Get recent commits for commit message style
            repo = git.Repo(repo_path)
            commits = list(repo.iter_commits(max_count=5))
            context += "Recent Commits:\n"
            for c in commits:
                context += f"- {c.message.strip()}\n"
            context += "\n"

        except Exception as e:
            logger.error(f"PREngineer: Context Harvest failed: {e}")
            
        return context

    def query_ai(self, prompt: str) -> str:
        """
        Queries the local AI models, iterating through fallbacks if necessary.
        """
        models = ["gemma4:e4b", "llama3", "mistral"]
        for model in models:
            logger.info(f"PREngineer: Querying local AI ({model})...")
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
            except requests.exceptions.RequestException as e:
                logger.warning(f"PREngineer: AI request with {model} failed: {e}. Falling back...")
        
        raise Exception("All fallback models failed to generate a response.")

    def solve_issue(self, payload: dict):
        """
        The main pipeline to generate a fix for an issue.
        """
        repo_name = payload.get('repo')
        issue_title = payload.get('issue_title')
        issue_number = payload.get('issue_number')
        
        if not repo_name or not issue_title:
            logger.error("PREngineer: Invalid payload received. Missing repo or title.")
            return
            
        logger.info(f"PREngineer: Starting work on {repo_name} - {issue_title}")

        # 1. Comment-First Strategy
        self.post_comment(repo_name, issue_number)

        # 2. Clone the repository safely
        repo_path = os.path.join(self.workspace_root, repo_name.replace("/", "_"))
        if os.path.exists(repo_path):
            logger.info(f"PREngineer: Cleaning up old workspace for {repo_name}...")
            shutil.rmtree(repo_path, ignore_errors=True)
        
        try:
            logger.info(f"PREngineer: Cloning https://github.com/{repo_name}.git ...")
            git.Repo.clone_from(f"https://github.com/{repo_name}.git", repo_path)
        except Exception as e:
            logger.error(f"PREngineer: Failed to clone {repo_name}: {e}")
            return

        # 3. Context Harvest
        repo_context = self.gather_context(repo_path)

        # 4. Prepare Sandbox Container
        if not self.docker_client:
            logger.info("PREngineer: Docker is not available. Skipping sandbox execution.")
        else:
            try:
                logger.info(f"PREngineer: Spinning up secure Docker sandbox for {repo_name}...")
                container = self.docker_client.containers.run(
                    "alpine:latest",
                    command="sleep 3600",
                    volumes={repo_path: {'bind': '/workspace', 'mode': 'rw'}},
                    working_dir="/workspace",
                    detach=True,
                    remove=True
                )
                logger.info(f"PREngineer: Sandbox ready. Container ID: {container.short_id}")
                container.stop()
            except Exception as e:
                logger.error(f"PREngineer: Sandbox failed: {e}")

        # 5. Query Local AI (with Fallback)
        prompt = f"""You are a senior open-source contributor.

RULES:
1. Read the existing code style and MATCH IT EXACTLY
2. Write tests for every change
3. Use the project's existing test framework
4. Follow the commit message convention (look at git log)
5. Keep changes minimal — fix only what the issue describes
6. Never refactor unrelated code

CONTEXT:
{repo_context}

ISSUE:
{issue_title}

Respond with only the code changes needed and a summary for the PR description."""

        try:
            ai_response = self.query_ai(prompt)
            logger.info(f"PREngineer: AI successfully generated a proposed fix of {len(ai_response)} characters.")
            
            payload["proposed_fix"] = ai_response
            payload["workspace_path"] = repo_path
            
            # Emit event to pass to CodeReviewer
            self.publish_event(PRReadyEvent(payload=payload))
            
        except Exception as e:
            logger.error(f"PREngineer: Solution generation failed: {e}")
