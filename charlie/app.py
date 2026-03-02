"""Charlie — Slack Socket Mode bridge for AudioWorld.

Relays messages between Slack and the Claude Code lead's tmux pane
via inbox/outbox JSON files.
"""

import logging
import os
import time
from pathlib import Path
from threading import Thread

import ssl

import certifi
from dotenv import load_dotenv

# Load .env BEFORE importing config (which reads env vars at import time)
load_dotenv(Path(__file__).parent / ".env")

# Fix macOS Python SSL — set globally so all libs (including websocket) use it
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["WEBSOCKET_CLIENT_CA_BUNDLE"] = certifi.where()

# Create a reusable SSL context for the whole app
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from charlie import bridge, config

logging.basicConfig(level=logging.INFO)

app = App(token=config.SLACK_BOT_TOKEN)

# Get bot's own user ID so we can detect @mentions in message events
_bot_user_id = None
try:
    _auth = app.client.auth_test(ssl=SSL_CONTEXT)
    _bot_user_id = _auth["user_id"]
    logging.info(f"Charlie bot user ID: {_bot_user_id}")
except Exception as e:
    logging.warning(f"Could not get bot user ID: {e}")


# Threads Charlie has posted in — replies here are processed
_charlie_threads: set[str] = set()


# ── Slack event handlers ─────────────────────────────────────────────

@app.event("message")
def handle_message(event, say, logger):
    """Process messages only when Charlie is @mentioned or replied to in its threads."""
    # Ignore bot's own messages
    if event.get("bot_id") or event.get("subtype"):
        return

    text = event.get("text", "")
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event.get("ts")
    user = event.get("user", "unknown")

    # Check if Charlie is @mentioned in the message
    is_mention = _bot_user_id and f"<@{_bot_user_id}>" in text

    # Check if this is a reply in a thread Charlie participated in
    is_charlie_thread = event.get("thread_ts") and event["thread_ts"] in _charlie_threads

    # Privacy: only process @mentions and Charlie-thread replies.
    # All other channel messages are ignored.
    if not is_mention and not is_charlie_thread:
        return

    # Strip bot mention from text if present
    import re
    clean_text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip() if is_mention else text

    if is_mention and not clean_text:
        # Empty mention — still route to lead so Charlie can respond in character
        clean_text = "(empty mention — user pinged Charlie without a message)"

    logger.info(f"Processing {'mention' if is_mention else 'thread reply'} from {user}: {clean_text[:80]}")

    # Write to inbox + nudge lead — no ack, the outbox response IS the reply
    msg_id = bridge.write_inbox(channel, user, clean_text, thread_ts)

    try:
        bridge.send_to_lead(msg_id)
    except Exception as e:
        logger.warning(f"tmux nudge failed: {e}")


@app.event("app_mention")
def handle_mention(event, say, logger):
    """Fallback for app_mention events (if subscribed). Handled by handle_message already."""
    pass


# ── Outbox watcher ───────────────────────────────────────────────────

def outbox_callback(data: dict) -> None:
    """Post an outbox message back to Slack."""
    thread_ts = data.get("thread_ts")
    app.client.chat_postMessage(
        channel=data["channel"],
        text=data["text"],
        thread_ts=thread_ts,
    )
    # Track this thread so future replies are processed
    if thread_ts:
        _charlie_threads.add(thread_ts)


# ── Sprint-prep monitor ─────────────────────────────────────────────

def monitor_sprint_prep() -> None:
    """Watch sprint-prep/ for new or modified .md files and notify Slack."""
    mtimes: dict[str, float] = {}
    channel = config.SLACK_CHANNEL_ID

    # Seed initial mtimes
    if config.SPRINT_PREP_DIR.exists():
        for f in config.SPRINT_PREP_DIR.glob("*.md"):
            mtimes[str(f)] = f.stat().st_mtime

    while True:
        time.sleep(config.FILE_POLL_INTERVAL)
        if not channel or not config.SPRINT_PREP_DIR.exists():
            continue
        try:
            for f in config.SPRINT_PREP_DIR.glob("*.md"):
                key = str(f)
                mtime = f.stat().st_mtime
                if key not in mtimes:
                    app.client.chat_postMessage(
                        channel=channel,
                        text=f"New sprint-prep sheet: `{f.name}`",
                    )
                elif mtime > mtimes[key]:
                    app.client.chat_postMessage(
                        channel=channel,
                        text=f"Sprint-prep sheet updated: `{f.name}`",
                    )
                mtimes[key] = mtime
        except OSError:
            pass


# ── Alert monitor ────────────────────────────────────────────────────

def monitor_alerts() -> None:
    """Periodically scan tmux output for alert keywords and notify Slack."""
    channel = config.SLACK_CHANNEL_ID
    while True:
        time.sleep(config.ALERT_POLL_INTERVAL)
        if not channel or not bridge.is_lead_alive():
            continue
        try:
            output = bridge.capture_lead_output(lines=30)
            alerts = bridge.detect_alerts(output)
            if alerts:
                app.client.chat_postMessage(
                    channel=channel,
                    text=f"Alert detected in tmux: {', '.join(alerts)}",
                )
        except Exception:
            pass


# ── Scheduler ───────────────────────────────────────────────────────

def run_scheduler() -> None:
    """Check schedule.json every minute and fire triggers at the right time.

    Triggers with needs_lead=true write to inbox + nudge the lead.
    The lead processes them like any Slack message and responds via outbox.
    """
    import json as _json
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    fired_today: set[str] = set()  # trigger IDs already fired today
    last_date: str = ""

    while True:
        time.sleep(config.SCHEDULER_POLL_INTERVAL)
        try:
            if not config.SCHEDULE_FILE.exists():
                continue

            schedule = _json.loads(config.SCHEDULE_FILE.read_text())
            tz = ZoneInfo(schedule.get("timezone", "Asia/Kolkata"))
            now = _dt.now(tz)
            today_str = now.strftime("%Y-%m-%d")
            today_day = now.strftime("%a").lower()  # mon, tue, etc.
            current_time = now.strftime("%H:%M")

            # Reset fired set on new day
            if today_str != last_date:
                fired_today.clear()
                last_date = today_str

            for trigger in schedule.get("triggers", []):
                tid = trigger["id"]
                if tid in fired_today:
                    continue
                if today_day not in trigger.get("days", []):
                    continue
                if current_time < trigger["time"]:
                    continue

                # Fire this trigger
                fired_today.add(tid)
                channel = config.SLACK_CHANNEL_ID
                message = trigger["message"]

                logging.info(f"Scheduler firing: {trigger['name']}")

                if trigger.get("needs_lead"):
                    # Write to inbox so the lead processes it
                    msg_id = bridge.write_inbox(
                        channel or "", "scheduler", message
                    )
                    try:
                        bridge.send_to_lead(msg_id)
                    except Exception as e:
                        logging.warning(f"Scheduler nudge failed: {e}")
                elif channel:
                    # Simple notification — post directly to Slack
                    app.client.chat_postMessage(
                        channel=channel, text=message
                    )

        except Exception as e:
            logging.warning(f"Scheduler error: {e}")


# ── Keep-alive ──────────────────────────────────────────────────────

def pulse() -> None:
    """Send a heartbeat to the lead pane every 10 minutes to prevent idle timeout."""
    while True:
        time.sleep(600)  # 10 minutes
        try:
            if bridge.is_lead_alive():
                bridge.send_to_lead_raw("pulse")
        except Exception:
            pass


# ── Connection lifecycle logging ────────────────────────────────────

def _on_ws_error(e: Exception):
    logging.error(f"[socket-mode] WebSocket error: {e}")

def _on_ws_close(code: int, reason: str | None):
    logging.warning(f"[socket-mode] WebSocket closed: code={code}, reason={reason}")

def _on_ws_message(msg: str):
    if '"type":"hello"' in msg:
        logging.info("[socket-mode] Connected (hello received)")
    elif '"type":"disconnect"' in msg:
        logging.warning("[socket-mode] Disconnect requested by Slack (normal refresh)")


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    import math

    if not config.SLACK_BOT_TOKEN or not config.SLACK_APP_TOKEN:
        print("Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set.")
        print("Copy charlie/.env.example to charlie/.env and fill in your tokens.")
        raise SystemExit(1)

    print("Starting Charlie - Slack bridge for AudioWorld")

    # Background threads
    Thread(target=bridge.watch_outbox, args=(outbox_callback,), daemon=True).start()
    Thread(target=monitor_sprint_prep, daemon=True).start()
    Thread(target=monitor_alerts, daemon=True).start()
    Thread(target=run_scheduler, daemon=True).start()
    # Pulse disabled — re-enable when needed
    # Thread(target=pulse, daemon=True).start()

    print(f"  Outbox watcher: polling every {config.OUTBOX_POLL_INTERVAL}s")
    print(f"  Sprint-prep monitor: polling every {config.FILE_POLL_INTERVAL}s")
    print(f"  Alert monitor: polling every {config.ALERT_POLL_INTERVAL}s")
    print(f"  Scheduler: checking every {config.SCHEDULER_POLL_INTERVAL}s")
    print(f"  Pulse: every 600s")
    print(f"  tmux target: {config.TMUX_LEAD_TARGET}")
    print("  Connecting to Slack via Socket Mode...")

    attempt = 0
    max_backoff = 300  # 5 minutes cap

    while True:
        try:
            handler = SocketModeHandler(
                app=app,
                app_token=config.SLACK_APP_TOKEN,
                auto_reconnect_enabled=True,
                ping_interval=10,
                trace_enabled=False,
                ping_pong_trace_enabled=False,
            )
            # Attach connection lifecycle listeners
            handler.client.on_error_listeners.append(_on_ws_error)
            handler.client.on_close_listeners.append(_on_ws_close)
            handler.client.on_message_listeners.append(_on_ws_message)

            attempt = 0  # Reset on successful start
            handler.start()  # Blocks until hard failure

        except KeyboardInterrupt:
            print("\nShutting down Charlie.")
            raise SystemExit(0)

        except Exception as e:
            attempt += 1
            backoff = min(5 * math.pow(2, attempt - 1), max_backoff)
            logging.error(f"[socket-mode] Hard failure (attempt {attempt}): {e}")
            logging.info(f"[socket-mode] Reconnecting in {backoff:.0f}s...")
            time.sleep(backoff)


if __name__ == "__main__":
    main()
