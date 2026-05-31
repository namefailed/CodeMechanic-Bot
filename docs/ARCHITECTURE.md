# CodeMechanic-Bot Architecture

CodeMechanic-Bot uses an event-driven, multi-agent architecture. The system is designed around a central `EventBus` in `orchestrator.py` that fully decouples the agents, allowing them to scale and fail independently.

## The Event Pipeline

When you run `python orchestrator.py`, the orchestrator enters an infinite loop. Every 30 minutes, it triggers the `BountyRadar` to start a scan cycle.

1. **BountyRadar**: Queries GitHub for issues with specific labels (`bounty`, `algora`, `polar`). It filters out saturated issues and emits a `BOUNTY_FOUND` event.
2. **ScamDetector**: Listens for `BOUNTY_FOUND`. It queries the repository's statistics. If the repo has < 5 stars, 0 historically merged PRs, or > 50 open issues, it kills the pipeline for that issue. Otherwise, it emits `BOUNTY_VERIFIED`.
3. **StaticAnalyzer**: Runs continuously in the background to proactively audit popular repositories (via `docker`). Runs `Semgrep` (logic bugs), `Trivy` (IaC and CVEs), and `Gitleaks` (secrets). Emits `BOUNTY_VERIFIED` for zero-days found.
4. **PREngineer**: Listens for `BOUNTY_VERIFIED`. 
   - Uses the GitHub API to post a "Comment First" message proposing to work on the issue.
   - Clones the repository locally.
   - Harvests context (tests, `CONTRIBUTING.md`, recent commits).
   - Queries the local AI (`gemma3:4b`, with fallbacks to `llama3` and `mistral`) to generate a targeted patch.
   - Tests the patch in a sandboxed Docker container (with daemon reconnection resilience).
   - Emits `PR_READY`.
5. **CodeReviewer**: Listens for `PR_READY`.
   - Has the AI self-review the generated patch for security and style.
   - If approved, it uses the GitHub CLI (`gh`) and robust git branching (`checkout -B`) to fork the repository, commit the patch, and open a Pull Request.
   - Emits `PR_SUBMITTED`.
6. **ContentEngine** / **DevOpsMonitor** / **EarningsTracker**: All listen for `PR_SUBMITTED` in parallel.
   - `ContentEngine`: Writes a markdown blog post detailing the automated fix.
   - `DevOpsMonitor`: Simulates tracking the CI/CD pipeline of the PR.
   - `EarningsTracker`: Maintains a local ledger of estimated ROIs.
7. **ReviewTracker** & **PRMaintainer**: Run continuously alongside the radar, polling the bot's open PRs. `ReviewTracker` watches for formal "changes requested" reviews (emitting `PR_REVIEWED`); `PRMaintainer` watches for new maintainer comments (emitting `MAINTAINER_FEEDBACK`). Both route back to the `PREngineer` to iteratively fix the code.

## Premium Web Dashboard

The backend communicates natively with a lightweight `FastAPI` server (`api/main.py`). The frontend (`ui/`) uses a beautiful Catppuccin Mocha theme with glassmorphism to control the bot. It embeds `CodeMirror` (with Vim mode enabled) so humans can intercept and review PRs manually if `manual_approval` is required in the config.

## Config & Model Fallbacks

The system behavior is defined in `config.yaml`.
Crucially, the bot implements a "Model Fallback" system. If the primary model fails or times out, it automatically tries the next models in the fallback array to ensure 24/7 uptime.
