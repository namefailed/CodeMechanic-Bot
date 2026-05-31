import os
import json
import requests
import sqlite3

def clean_prs():
    token = None
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip()
    
    if not token:
        print("No GITHUB_TOKEN found.")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get user
    user_res = requests.get("https://api.github.com/user", headers=headers)
    if user_res.status_code != 200:
        print("Failed to get user:", user_res.text)
        return
    
    login = user_res.json().get("login")
    print(f"Authenticated as {login}")

    # Find all PRs by user
    search_url = f"https://api.github.com/search/issues?q=author:{login}+is:pr"
    search_res = requests.get(search_url, headers=headers)
    if search_res.status_code != 200:
        print("Search failed:", search_res.text)
        return
        
    items = search_res.json().get("items", [])
    
    active_pr_urls = []

    for pr in items:
        pr_url = pr.get("html_url")
        pr_api_url = pr.get("url")
        repo_url = pr.get("repository_url")
        repo_name = repo_url.replace("https://api.github.com/repos/", "")
        
        pr_data = requests.get(pr_api_url, headers=headers).json()
        state = pr_data.get("state")
        merged = pr_data.get("merged", False)
        
        print(f"PR {pr_url} - State: {state}, Merged: {merged}")
        
        if state == "closed":
            print(f"Removing fork and cleaning DB for {repo_name} because PR is closed/merged.")
            # Remove fork
            fork_name = f"{login}/{repo_name.split('/')[-1]}"
            del_url = f"https://api.github.com/repos/{fork_name}"
            del_res = requests.delete(del_url, headers=headers)
            print(f"Delete fork response: {del_res.status_code}")
        else:
            active_pr_urls.append(pr_url)
            print(f"Keeping {pr_url} as it is still open.")

    # Clean DB
    db_path = "bounty_tracker.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get all issues in DB
        cur.execute("SELECT issue_url, repo_name FROM processed_issues")
        db_issues = cur.fetchall()
        
        for row in db_issues:
            issue_url = row[0]
            repo_name = row[1]
            
            # Find the PR URL that corresponds to this issue. The DB stores issue_url.
            # We can just check the PRs directly. If the issue is closed, we remove it from DB.
            issue_api_url = issue_url.replace("https://github.com/", "https://api.github.com/repos/").replace("/issues/", "/issues/")
            iss_res = requests.get(issue_api_url, headers=headers)
            if iss_res.status_code == 200:
                iss_state = iss_res.json().get("state")
                if iss_state == "closed":
                    print(f"Issue {issue_url} is closed. Removing from DB.")
                    cur.execute("DELETE FROM processed_issues WHERE issue_url = ?", (issue_url,))
            
        conn.commit()
        conn.close()
        print("DB cleaned.")

if __name__ == "__main__":
    clean_prs()
