"""Core relay module — file I/O and tmux integration. No Slack dependency."""

import json
import os
import re
import string
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from random import choices
from typing import Callable

from charlie import config


def _random_id() -> str:
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(choices(chars, k=4))
    return f"msg-{int(time.time())}-{suffix}"


def log_exchange(direction: str, user: str, text: str, msg_id: str,
                 channel: str = "", thread_ts: str = "") -> None:
    """Append an exchange to the daily JSONL log."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = config.LOGS_DIR / f"{today}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "direction": direction,  # "in" or "out"
        "user": user,
        "msg_id": msg_id,
        "channel": channel,
        "thread_ts": thread_ts,
        "text": text[:2000],  # cap to avoid huge entries
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def write_inbox(channel: str, user: str, text: str, thread_ts: str | None = None) -> str:
    """Write a Slack message to the inbox as JSON. Returns the message ID."""
    msg_id = _random_id()
    payload = {
        "id": msg_id,
        "channel": channel,
        "user": user,
        "text": text,
        "thread_ts": thread_ts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = config.INBOX_DIR / f"{msg_id}.json"
    path.write_text(json.dumps(payload, indent=2))
    log_exchange("in", user, text, msg_id, channel, thread_ts or "")
    return msg_id


def send_to_lead(msg_id: str) -> None:
    """Send a nudge to the lead's tmux pane to process an inbox file.

    Text and Enter are sent as separate tmux commands with a delay so
    Claude Code's TUI treats Enter as 'submit', not 'newline inside paste'.
    """
    cmd = f"Process Slack message from charlie/inbox/{msg_id}.json"
    target = config.TMUX_LEAD_TARGET
    # Send text literally (no key-name interpretation)
    subprocess.run(["tmux", "send-keys", "-t", target, "-l", cmd], check=True)
    # Small delay lets the TUI finish processing the pasted text
    time.sleep(0.3)
    # Send Enter as a separate keystroke → triggers submit
    subprocess.run(["tmux", "send-keys", "-t", target, "Enter"], check=True)


def send_to_lead_raw(text: str) -> None:
    """Send raw text to the lead's tmux pane without writing an inbox file.
    Used for keep-alive pings and lightweight nudges."""
    target = config.TMUX_LEAD_TARGET
    subprocess.run(["tmux", "send-keys", "-t", target, "-l", text], check=True)
    time.sleep(0.3)
    subprocess.run(["tmux", "send-keys", "-t", target, "Enter"], check=True)


def watch_outbox(callback: Callable[[dict], None]) -> None:
    """Poll outbox/ for new JSON files and relay them via callback. Runs forever."""
    seen: set[str] = set()
    while True:
        try:
            for path in config.OUTBOX_DIR.glob("*.json"):
                if path.name in seen:
                    continue
                try:
                    data = json.loads(path.read_text())
                    callback(data)
                    log_exchange("out", "charlie", data.get("text", ""),
                                data.get("id", ""), data.get("channel", ""),
                                data.get("thread_ts", ""))
                    path.unlink()
                except (json.JSONDecodeError, OSError) as exc:
                    print(f"[outbox] Error processing {path.name}: {exc}")
                seen.add(path.name)
        except OSError:
            pass
        time.sleep(config.OUTBOX_POLL_INTERVAL)


def capture_lead_output(lines: int = 50) -> str:
    """Capture recent output from the lead's tmux pane, stripped of ANSI codes."""
    target = config.TMUX_LEAD_TARGET
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", target, "-p", f"-S", f"-{lines}"],
        capture_output=True,
        text=True,
    )
    raw = result.stdout
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", raw)


def is_lead_alive() -> bool:
    """Check if the tmux session hosting the lead is still running."""
    session = config.TMUX_LEAD_TARGET.split(":")[0]
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    return result.returncode == 0


def detect_alerts(text: str) -> list[str]:
    """Scan text for alert keywords (case-insensitive). Returns matched keywords."""
    lower = text.lower()
    return [kw for kw in config.ALERT_KEYWORDS if kw.lower() in lower]


# ── Self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing bridge write_inbox / read-back...")
    mid = write_inbox("C_TEST", "U_TEST", "hello from bridge self-test")
    path = config.INBOX_DIR / f"{mid}.json"
    data = json.loads(path.read_text())
    assert data["text"] == "hello from bridge self-test"
    assert data["channel"] == "C_TEST"
    path.unlink()
    print(f"  ✓ wrote + read + cleaned up {mid}")
    print("Bridge self-test passed.")
