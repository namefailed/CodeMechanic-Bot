# Bug-Bot 🕷️💰

**Bug-Bot** is an autonomous, multi-agent AI system designed to hunt down paid open-source bounties across GitHub, Algora, and Polar, write the code fixes, and submit pull requests—all while you sleep.

It was heavily inspired by the "ZKA Money Printer" experiments, but has been heavily refactored to be **100% autonomous**, robust, and actually profitable by avoiding scams and saturated bounties.

## Key Features

- **Patience Harvest & Speed Game**: Scans for abandoned bounties (>14 days old) and brand new bounties (<48 hours) to minimize competition.
- **Scam Detection**: Automatically rejects honeypots and scam repositories that harvest free labor (e.g. repos with <5 stars or 0 historically merged PRs).
- **Multi-Source Support**: Scans native GitHub bounties, as well as `algora` and `polar` labeled issues.
- **Comment-First Strategy**: Posts a comment proposing a fix *before* doing the heavy lifting, building trust with maintainers.
- **Context Harvesting**: Clones the repo to read `CONTRIBUTING.md` and commit history to ensure the AI's code matches the project's style perfectly.
- **Context RAG**: Parses issue bodies and comments to extract referenced filenames, automatically injecting their source code into the LLM context so it never writes code blindly.
- **Docker Auto-Testing**: Spins up an Alpine container, dynamically installs the required toolchain (Node, Python, Rust), and executes the repository's test suite against the AI's generated code.
- **Self-Healing LLM**: If local unit tests fail, the stderr logs are fed *back* into the LLM for up to 2 autonomous retry attempts before submitting.
- **Multi-Model Fallbacks**: Uses `gemma4:e4b` locally via Ollama, but gracefully falls back to `llama3` or `mistral` if the primary model fails.
- **Stealth Mode**: Commits directly to the workspace using standard git credentials and submits via the API, preventing "bot" labels on your PRs.

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: A deep dive into the 7-agent EventBus system.
- **[User Guide](docs/USER_GUIDE.md)**: An extremely simple, step-by-step guide on how to configure and run the bot.

## Quick Start

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Start your local Ollama server (or configure your preferred LLM in `config.yaml`).
3. Create a `.env` file in the root directory and add your GitHub Token:
   ```text
   GITHUB_TOKEN=your_personal_access_token
   ```
4. Run the orchestrator in stealth mode:
   ```bash
   python orchestrator.py --stealth
   ```

## Disclaimer
This bot is designed to contribute meaningfully to open-source software. Please do not use it to spam repositories with low-quality, AI-generated fluff.
