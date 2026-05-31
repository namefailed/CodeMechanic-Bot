# User Guide for CodeMechanic-Bot

Hello! If you are new to coding, APIs, or AI agents, don't worry — this guide walks you through getting CodeMechanic-Bot running step by step.

## Step 1: What You Need First
1. **Python 3.11+** — the language the bot is built in.
2. **A GitHub account + token** — the bot uses your account to hunt bounties and submit code.
3. **Ollama** — runs the local AI model that writes the fixes. Install from <https://ollama.com>.
4. *(Optional, recommended)* **Docker Desktop** — lets the bot test its fixes in a sandbox and run the zero-day researcher. The bot still works without it; the generated fixes just aren't test-checked.

## Step 2: Get a GitHub Token
1. Log into GitHub.
2. Go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**.
3. Click **Generate new token (classic)**.
4. Check the **`repo`** box.
5. Generate it and copy it somewhere safe. It looks like `ghp_something123`.

## Step 3: Set Up the Project
1. Open a terminal and `cd` into the `CodeMechanic-Bot` folder.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows (use source .venv/bin/activate on macOS/Linux)
   pip install -r requirements.txt
   ```
3. Create a file named `.env` in the project folder with your token (this file is gitignored, so it never leaves your machine):
   ```
   GITHUB_TOKEN=ghp_your_token_here
   ```
4. Pull the local AI model (must match `config.yaml`):
   ```bash
   ollama pull gemma3:4b
   ```

## Step 4: Run the Dashboard
1. Start the web server from the same virtualenv (loopback only — it holds your token):
   ```bash
   uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```
   > ⚠️ Don't use `--host 0.0.0.0` — that exposes your token and bot controls to your whole network.
2. Open <http://127.0.0.1:8000> — you'll see the Catppuccin Mocha dashboard.
3. Click **Start Bot**.

## What Happens Next?
The bot runs two loops. Every 30 minutes the bounty hunter:
- Scours GitHub for new bug bounties.
- Throws away the fake/scam ones.
- Reads the code of the good ones and asks the local AI for a minimal fix.
- Tests the fix in a Docker sandbox (if Docker is running).
- Posts a short "comment-first" note on the issue, then **queues the patch in the Approvals tab** for you to review.

> By default `manual_approval: true` in `config.yaml`, so the bot waits for your approval (in the **Approvals** tab) before opening a real PR. Set it to `false` for fully autonomous submission. Watch the live terminal logs in the dashboard to see the bot working — when it submits a fix you'll see `PR created successfully!` and it writes a short post in `blog_posts/`.
