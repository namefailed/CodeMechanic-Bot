import requests, os, sys
sys.stdout.reconfigure(encoding='utf-8')
token = [line.strip().split('=', 1)[1] for line in open('.env') if line.startswith('GITHUB_TOKEN=')][0]
headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
user = requests.get('https://api.github.com/user', headers=headers).json()['login']

print(f'=== Scanning GitHub for user: {user} ===')

print('\n--- FORKS ---')
repos = requests.get(f'https://api.github.com/users/{user}/repos?type=owner&per_page=100', headers=headers).json()
forks = [r for r in repos if r.get('fork')]
for f in forks:
    print(f['full_name'], '-', f['html_url'])

print('\n--- PRs AUTHORED ---')
prs = requests.get('https://api.github.com/search/issues', headers=headers, params={'q': f'author:{user} is:pr created:>=2026-05-28'}).json().get('items', [])
for pr in prs:
    print(f"[{pr['state'].upper()}] {pr['title']} - {pr['html_url']}")

print('\n--- RECENT COMMENTS/REPLIES ON OUR PRS ---')
for pr in prs:
    pr_comments_url = pr['comments_url']
    comments = requests.get(pr_comments_url, headers=headers).json()
    if comments:
        print(f"\nReplies on {pr['html_url']}:")
        for c in comments:
            print(f"  [{c['user']['login']}]: {c['body'][:200]}")
