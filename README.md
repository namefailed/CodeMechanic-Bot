# CodeMechanic-Bot 🤖🔧

**CodeMechanic-Bot** is an autonomous, multi-agent AI system designed to hunt down paid open-source bounties AND proactively discover zero-day vulnerabilities in popular repositories.

Built on an event-driven architecture, it operates with strict anti-slop guidelines to ensure that all generated code is highly original, rigorously tested, and perfectly matches the target repository's style.

## The Dual-Thread Engine

The bot's Orchestrator runs two concurrent, highly synchronized loops:

### 1. The Bounty Hunter
Runs every 30 minutes to scan GitHub, Algora, and Polar for low-competition, high-value paid bounties.
- **Patience Harvest & Speed Game**: Targets abandoned bounties or brand new ones.
- **Scam Detection**: Automatically rejects honeypots and saturated repos.

### 2. The Zero-Day Researcher
Runs continuously in the background (pausing only when the Bounty Hunter wakes up) to audit massive open-source repositories for unknown vulnerabilities.
- **Semgrep**: Scans for complex logic bugs and syntax vulnerabilities.
- **Trivy**: Scans for Infrastructure-as-Code misconfigurations and outdated CVEs.
- **Gitleaks**: Hunts for leaked API keys, database credentials, and webhooks (flagging them for manual review rather than public PRs).

## Core Capabilities

- **Strict Anti-Slop CodeReviewer**: A notoriously strict secondary agent that audits every generated patch. It will violently reject any proposed PR that smells like "AI Slop", removes necessary comments, or fails to precisely match the host repository's style. Uses robust Git branching (`checkout -B`) to ensure pristine states during retries.
- **Few-Shot RAG Context**: Parses issue bodies and securely injects only highly-relevant source code into the local LLM's context, strictly capped to prevent hallucination on weaker machines.
- **Docker Auto-Testing**: Spins up a language-specific container (Node, Python, Rust, Go, Java, Ruby, PHP) and executes the repository's test suite against the AI's generated code. Dynamically reconnects to Docker daemons to survive host restarts.
- **Self-Healing LLM**: If local unit tests fail, the stderr logs are fed *back* into the LLM for up to 2 autonomous retry attempts before submitting.
- **Multi-Model Fallbacks**: Uses `gemma3:4b` locally via Ollama, but gracefully falls back to `llama3` or `mistral` if the primary model fails. Models are configurable in `config.yaml`.
- **Premium Web Dashboard**: A built-in FastAPI web dashboard featuring a stunning Catppuccin Mocha theme, glassmorphism UI, and a fully functional CodeMirror editor with Vim keybindings for manual config overrides.

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: A deep dive into the 10-agent EventBus system.
- **[User Guide](docs/USER_GUIDE.md)**: An extremely simple, step-by-step guide on how to configure and run the bot.

## Quick Start

1. Create a virtualenv and install requirements:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows (PowerShell/cmd) — use source .venv/bin/activate on *nix
   pip install -r requirements.txt
   ```
2. Add your GitHub token to a `.env` file in the project root (gitignored):
   ```
   GITHUB_TOKEN=ghp_your_token_here
   ```
3. Pull at least one local model with Ollama (must match `config.yaml`):
   ```bash
   ollama pull gemma3:4b
   ```
4. *(Optional, recommended)* Start Docker Desktop. Without it, generated patches are **not** test-validated in a sandbox and the zero-day researcher is disabled — the bounty bot still runs.
5. Start the dashboard **from the same virtualenv** (loopback only — it holds your token and can start the bot):
   ```bash
   uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```
   > ⚠️ Do not bind to `0.0.0.0` / expose this dashboard on a network without adding authentication first.
6. Open <http://127.0.0.1:8000> and click "Start Bot".

> **First run:** `manual_approval: true` is set in `config.yaml`, so each AI patch is queued in the **Approvals** tab for you to review before it opens a real PR. The bot still posts a "comment-first" message on issues once it has a working fix. Set `manual_approval: false` for fully autonomous submission.

## Disclaimer
This machine account is operated heavily by @namefailed. It strictly adheres to anti-slop principles. Do not abuse this architecture to spam repositories with low-quality, AI-generated fluff.
