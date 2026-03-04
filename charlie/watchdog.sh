#!/usr/bin/env bash
# watchdog.sh - Monitor Claude Code in lead pane, restart if dead.
# Runs as audioworld-watchdog.service (MemoryMax=64M).

SESSION="audioworld"
WINDOW="lead"
PROJECT_DIR="/root/Desktop/audioworld"
CHECK_INTERVAL=30
DEAD_THRESHOLD=4  # 4 checks * 30s = 2 minutes before restart

dead_count=0

echo "[watchdog] Started. Checking ${SESSION}:${WINDOW} every ${CHECK_INTERVAL}s."

while true; do
    # Get the shell PID inside the lead pane
    pane_pid=$(tmux list-panes -t "${SESSION}:${WINDOW}" -F "#{pane_pid}" 2>/dev/null | head -1)

    if [ -z "$pane_pid" ]; then
        dead_count=$((dead_count + 1))
        echo "[watchdog] $(date -u +%H:%M:%S) Pane not found. Count: ${dead_count}/${DEAD_THRESHOLD}"
    else
        # Check if claude is running as a child of the pane shell
        if pgrep -P "$pane_pid" -f "claude" > /dev/null 2>&1; then
            dead_count=0
        else
            dead_count=$((dead_count + 1))
            echo "[watchdog] $(date -u +%H:%M:%S) Claude not running. Count: ${dead_count}/${DEAD_THRESHOLD}"
        fi
    fi

    if [ "$dead_count" -ge "$DEAD_THRESHOLD" ]; then
        echo "[watchdog] $(date -u +%H:%M:%S) Lead dead for ${DEAD_THRESHOLD} checks. Restarting..."

        # Restart Claude Code in the lead pane
        tmux send-keys -t "${SESSION}:${WINDOW}" "cd ${PROJECT_DIR} && claude" Enter

        # Drop a watchdog alert into Charlie's inbox
        msg_id="watchdog-$(date +%s)"
        cat > "${PROJECT_DIR}/charlie/inbox/${msg_id}.json" << ALERTEOF
{
  "id": "${msg_id}",
  "channel": "system",
  "user": "watchdog",
  "text": "[WATCHDOG] Claude Code was found dead and has been restarted. Check for unprocessed inbox messages.",
  "thread_ts": null,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
ALERTEOF

        dead_count=0
        # Extra wait for Claude to boot
        sleep 30
    fi

    sleep "$CHECK_INTERVAL"
done
