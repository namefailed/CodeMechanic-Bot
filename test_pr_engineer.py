from orchestrator import Orchestrator

def test():
    print("Testing PR Engineer...")
    bot = Orchestrator()
    
    # Mock payload simulating a verified bounty
    mock_payload = {
        "repo": "octocat/Hello-World",
        "issue_title": "Update README.md to say hello to Antigravity",
        "issue_url": "https://github.com/octocat/Hello-World/issues/1",
        "comments": 0
    }
    
    # Trigger PR Engineer directly
    bot.pr_engineer.solve_issue(mock_payload)

if __name__ == "__main__":
    test()
