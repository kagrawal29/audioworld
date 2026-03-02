# AudioWorld — LinkedIn Outreach System

Automated LinkedIn outreach for [Audio World](https://www.audioworld.in), a pan-India multilingual voiceover & dubbing company.

## What It Does

Runs a daily outreach cycle on LinkedIn — connection requests, post comments, and profile visits — targeting decision-makers in segments like Ad Agencies, Corporate Video, and E-Learning.

```
/prep [segment]  →  Build execution sheet (research + personalization)
/review          →  Quality check against standards
Approval Sheet   →  User approves/rejects each action in Google Sheets
/sprint          →  Execute approved actions on LinkedIn
/status          →  Check progress
```

## Architecture

The system runs on a DigitalOcean server (Ubuntu 24.04) with the user interacting via Slack.

```
┌─────────┐    Slack     ┌──────────┐    inbox/outbox    ┌────────────┐
│  User   │◄────────────►│ Charlie  │◄──────────────────►│   Lead     │
│ (Slack) │              │ (bridge) │                    │ (Claude)   │
└─────────┘              └──────────┘                    └─────┬──────┘
                                                               │
                                                    ┌──────────┼──────────┐
                                                    │          │          │
                                               ┌────▼───┐ ┌───▼────┐ ┌──▼───┐
                                               │ Helper │ │Operator│ │ Rube │
                                               │(research│ │(browser│ │(MCP) │
                                               │ sheets) │ │LinkedIn│ │Sheets│
                                               └────────┘ └────────┘ └──────┘
```

| Component | Description |
|-----------|-------------|
| **Charlie** | Slack Socket Mode bridge — relays messages, runs scheduler, monitors sprint-prep |
| **Lead** | Claude Code agent — coordinates the team, handles Slack, reviews work |
| **Helper** | Teammate agent — research, spreadsheet ops, data analysis |
| **Operator** | LinkedIn browser agent — controls Chromium via Playwright CDP |
| **Rube MCP** | Google Sheets/Drive/Gmail integration via Composio |

## Key Files

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | Operational playbook (loaded every session) |
| `SETUP.md` | Full server provisioning guide |
| `charlie/app.py` | Slack bridge + scheduler |
| `charlie/bridge.py` | File I/O relay, tmux integration |
| `charlie/CHARACTER.md` | Charlie's persona and voice |
| `charlie/schedule.json` | Scheduled triggers (briefings, git push) |
| `.claude/agents/linkedin-operator.md` | Browser operator agent definition |
| `.claude/skills/` | Slash command skills (`/prep`, `/sprint`, `/review`, `/status`) |
| `sprint-prep/field-manual.md` | Operator's playbook (pacing, selectors, limits) |
| `sprint-prep/YYYY-MM-DD-*.md` | Daily execution sheets |

## Safety

- **Proxy mandatory** — all LinkedIn traffic routes through a dedicated static Indian IP (Decodo). The server's datacenter IP never touches LinkedIn.
- **Nothing sends without approval** — every action goes through a Google Sheets approval flow before execution.
- **Human-like pacing** — rate limits, random delays, and daily caps protect the LinkedIn account.

## Setup

See [SETUP.md](SETUP.md) for complete server provisioning from scratch.
