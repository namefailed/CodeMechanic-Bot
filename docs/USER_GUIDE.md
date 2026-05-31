# User Guide for CodeMechanic-Bot

Hello! If you are new to coding, APIs, or AI agents, don't worry. This guide is written specifically for you. It will explain exactly how to get CodeMechanic-Bot running to earn bounties while you sleep.

## Step 1: What You Need First
Before you can run the bot, you need two things:
1. **Python**: The programming language the bot is built in.
2. **A GitHub Account**: The bot uses your account to hunt bounties and submit code.

## Step 2: Get a GitHub Token
The bot needs permission to read and write code on your behalf.
1. Log into GitHub.
2. Go to **Settings** -> **Developer settings** -> **Personal access tokens** -> **Tokens (classic)**.
3. Click **Generate new token (classic)**.
4. Check the box for `repo` (this gives it access to code).
5. Generate the token and **copy it down somewhere safe**. It will look like `ghp_something123`.

## Step 3: Run the Dashboard
1. Open your computer's terminal (or command prompt).
2. Use the `cd` command to navigate to the folder where `CodeMechanic-Bot` is saved.
3. Start the built-in web server by typing:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
4. Open your web browser and go to `http://localhost:8000`. You will see the beautiful Catppuccin Mocha dashboard!
5. In the dashboard's built-in CodeMirror editor (it has Vim bindings if you like!), put your token into the `config.yaml` file and hit **Save**.
6. Click **Start Bot**.

## What Happens Next?
That's it! You can leave the browser open. 

Every 30 minutes, the bot will:
- Scour the internet for new bug bounties.
- Throw away the fake/scam ones.
- Read the code of the good ones.
- Tell the AI how to fix the problem.
- Automatically upload the fix to GitHub (unless you configured manual approval in the dashboard).

You can watch the live terminal logs directly from the web dashboard to see the bot "thinking" and working. If it successfully submits a fix, you'll see a log message saying `Submitting PR for...` and it will write a small blog post in the `blog_posts/` folder!
