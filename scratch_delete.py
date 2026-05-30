import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
token = [line.strip().split('=', 1)[1] for line in open('.env') if line.startswith('GITHUB_TOKEN=')][0]
headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}

# Close open PRs
open_prs = [
    ('unjs', 'fontaine', 765)
]
for owner, repo, pull_num in open_prs:
    print(f"Closing PR {owner}/{repo}#{pull_num}")
    res = requests.patch(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_num}", headers=headers, json={"state": "closed"})
    if res.status_code == 200:
        print("Successfully closed PR.")
    else:
        print(f"Failed to close PR: {res.status_code} {res.text}")

# Delete Forks
forks_to_delete = [
    'namefailed/ContribAI',
    'namefailed/dramatiq',
    'namefailed/fontaine',
    'namefailed/monorepo',
    'namefailed/SewUp',
    'namefailed/gnome-shellext-system-menu-hide-items'
]

for f in forks_to_delete:
    print(f"Deleting fork: {f}")
    res = requests.delete(f"https://api.github.com/repos/{f}", headers=headers)
    if res.status_code == 204:
        print("Successfully deleted fork.")
    else:
        print(f"Failed to delete fork: {res.status_code} {res.text}")
