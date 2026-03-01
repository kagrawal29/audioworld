"""Paths, env vars, and constants for the Charlie bridge."""

import os
from pathlib import Path

# Directory layout
PROJECT_ROOT = Path(__file__).parent.parent  # audioworld/
CHARLIE_DIR = PROJECT_ROOT / "charlie"
INBOX_DIR = CHARLIE_DIR / "inbox"
OUTBOX_DIR = CHARLIE_DIR / "outbox"
LOGS_DIR = CHARLIE_DIR / "logs"
SCHEDULE_FILE = CHARLIE_DIR / "schedule.json"
SPRINT_PREP_DIR = PROJECT_ROOT / "sprint-prep"

# tmux — the lead runs in an existing tmux session
TMUX_LEAD_TARGET = os.getenv("CHARLIE_TMUX_TARGET", "audioworld:0.0")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Polling intervals (seconds)
OUTBOX_POLL_INTERVAL = 2       # check for outbox responses
FILE_POLL_INTERVAL = 30        # check sprint-prep changes
ALERT_POLL_INTERVAL = 10       # check tmux for alerts

# Alert keywords to watch for in tmux output
ALERT_KEYWORDS = [
    "captcha", "verification", "unusual activity",
    "rate limit", "FULL STOP", "restriction",
]

# Polling intervals for scheduler
SCHEDULER_POLL_INTERVAL = 60   # check schedule every 60s

# Ensure dirs exist on import
INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
