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

# tmux — resolved dynamically at send time (see bridge._resolve_lead_pane)
TMUX_LEAD_SESSION = os.getenv("CHARLIE_TMUX_SESSION", "audioworld")
TMUX_LEAD_WINDOW = os.getenv("CHARLIE_TMUX_WINDOW", "lead")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Polling intervals (seconds)
OUTBOX_POLL_INTERVAL = 2       # check for outbox responses
FILE_POLL_INTERVAL = 30        # check sprint-prep changes
ALERT_POLL_INTERVAL = 10       # check tmux for alerts

# Alert detection is now disabled. It caused false positives by matching
# keywords in normal conversation text. LinkedIn safety is handled by the
# operator agent, which reports issues directly via team messages.
ALERT_KEYWORDS = []

# Polling intervals for scheduler
SCHEDULER_POLL_INTERVAL = 60   # check schedule every 60s

# Ensure dirs exist on import
INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
