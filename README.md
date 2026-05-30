# Bug-Bot 🕷️💰

**Bug-Bot** is an autonomous, multi-agent AI system designed to hunt down paid open-source bounties across GitHub, Algora, and Polar, write the code fixes, and submit pull requests—all while you sleep.

It was heavily inspired by the "ZKA Money Printer" experiments, but has been heavily refactored to be **100% autonomous**, robust, and actually profitable by avoiding scams and saturated bounties.

## Key Features

- **Patience Harvest & Speed Game**: Scans for abandoned bounties (>14 days old) and brand new bounties (<48 hours) to minimize competition.
- **Scam Detection**: Automatically rejects honeypots and scam repositories that harvest free labor (e.g. repos with <5 stars or 0 historically merged PRs).
- **Multi-Source Support**: Scans native GitHub bounties, as well as `algora` and `polar` labeled issues.
- **Comment-First Strategy**: Posts a comment proposing a fix *before* doing the heavy lifting, building trust with maintainers.
- **Context Harvesting**: Clones the repo to read `CONTRIBUTING.md` and commit history to ensure the AI's code matches the project's style perfectly.
- **Multi-Model Fallbacks**: Uses `gemma4:e4b` locally via Ollama, but gracefully falls back to `llama3` or `mistral` if the primary model fails.

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: A deep dive into the 7-agent EventBus system.
- **[User Guide](docs/USER_GUIDE.md)**: An extremely simple, step-by-step guide on how to configure and run the bot.

## Quick Start

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Start your local Ollama server (or configure your preferred LLM in `config.yaml`).
3. Export your GitHub Token:
   ```bash
   export GITHUB_TOKEN="your_personal_access_token"
   ```
4. Run the orchestrator:
   ```bash
   python orchestrator.py
   ```

## Disclaimer
This bot is designed to contribute meaningfully to open-source software. Please do not use it to spam repositories with low-quality, AI-generated fluff.
