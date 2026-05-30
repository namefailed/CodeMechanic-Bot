# User Guide for Bug-Bot

Hello! If you are new to coding, APIs, or AI agents, don't worry. This guide is written specifically for you. It will explain exactly how to get Bug-Bot running to earn bounties while you sleep.

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

## Step 3: Run the Bot
1. Open your computer's terminal (or command prompt).
2. Use the `cd` command to navigate to the folder where `bug-bot` is saved.
3. Tell your computer about your GitHub token by typing:
   - On Windows: `set GITHUB_TOKEN=your_token_here`
   - On Mac/Linux: `export GITHUB_TOKEN="your_token_here"`
4. Start the bot by typing:
   ```bash
   python orchestrator.py
   ```

## What Happens Next?
That's it! You can walk away from your computer. 

Every 30 minutes, the bot will:
- Scour the internet for new bug bounties.
- Throw away the fake/scam ones.
- Read the code of the good ones.
- Tell the AI how to fix the problem.
- Automatically upload the fix to GitHub.

You can watch the terminal window to see the bot "thinking" and working. If it successfully submits a fix, you'll see a log message saying `Submitting PR for...` and it will write a small blog post in the `blog_posts/` folder!
