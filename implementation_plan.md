# Implementation Plan

## Goal Description
Build "ZKA Money Printer," an autonomous 24/7 Bug Bounty Bot designed to hunt GitHub bounties, identify real opportunities, submit pull requests, and track earnings. This project matches the proven architecture from the reference articles while incorporating advanced architectural ideas from leading open-source agents (like OpenHands, SWE-agent, and Open SWE). 

The setup will be optimized for a fresh Windows 11 installation on a high-end gaming laptop, leveraging local GPU resources for AI model inference (e.g., using Ollama with Gemma 4 or similar models) to minimize cloud costs and maintain privacy.

## Architecture

### Bootstrapping & Configuration
- **Dependencies**: Python 3.11+, Git, GitHub CLI, Ollama, Docker Desktop.
- **Config**: A `config.yaml` defining target keywords, AI model endpoints, and governance limits.

### Core Orchestration
- **Modular Event Bus**: Agents pass states and messages to each other (e.g., Bounty Radar emits a `BountyFoundEvent`, which triggers the Scam Detector, which then triggers the PR Submitter).
- **Scheduler**: Orchestrates the timed execution of scanning agents.

### The 7-Agent System & ACI
1. **Agent 1: Bounty Radar**: Scans GitHub for open issues and scores competition.
2. **Agent 2: PR Engineer (Submitter)**: 
   - Uses a strict **Agent-Computer Interface (ACI)** to search, view, and edit files, preventing syntax corruption.
   - **Sandboxing**: Spawns a lightweight Docker container to clone the repo, run the project's tests, and verify the AI's fix safely.
3. **Agent 3: Content Engine**: Drafts markdown articles detailing the bot's findings.
4. **Agent 4: Code Reviewer (CodeSentinel)**: Uses local AI to review PRs before submission.
5. **Agent 5: Scam Detector**: Checks repository legitimacy.
6. **Agent 6: DevOps Monitor**: Monitors CI pipelines for submitted PRs.
7. **Agent 7: Earnings Tracker**: Tracks bounty payouts and calculates ROI.

### Governance & Security
- **Tiered Permissions**: Actions like deleting branches or merging PRs require human approval.
- **Blacklists**: Maintains lists of known scam repos (e.g., `SecureBananaLabs`).

## Verification Plan
1. Test ACI commands within a dummy Docker container.
2. Test Scam Detector against known fake repos.
3. Observe agents scanning and evaluating real bounties in an isolated environment without submitting actual PRs initially.
