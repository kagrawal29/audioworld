#!/usr/bin/env bash
# watchdog.sh -- Monitor Claude Code in lead pane, restart if dead or auth-failed.
# Runs as audioworld-watchdog.service (MemoryMax=64M).
#
# Checks for TWO failure modes:
# 1. Process death: Claude Code process not running in the pane
# 2. Auth failure: 401/authentication_error in tmux scrollback (token expired)
#
# On auth failure: attempts token refresh before restarting Claude Code.

SESSION="${CHARLIE_TMUX_SESSION:-audioworld}"
WINDOW="${CHARLIE_TMUX_WINDOW:-lead}"
PROJECT_DIR="${CHARLIE_PROJECT_DIR:-/root/Desktop/audioworld}"
REFRESH_SCRIPT="${PROJECT_DIR}/charlie/refresh-token.sh"
INBOX_DIR="${PROJECT_DIR}/charlie/inbox"
CHECK_INTERVAL=30
DEAD_THRESHOLD=4        # 4 checks * 30s = 2 minutes before restart
AUTH_FAIL_THRESHOLD=2   # 2 checks * 30s = 1 minute before auth recovery

# Slack config -- loaded from project .env
ENV_FILE="${PROJECT_DIR}/charlie/.env"
if [ -f "$ENV_FILE" ]; then
    SLACK_BOT_TOKEN=$(grep '^SLACK_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
    SLACK_CHANNEL_ID=$(grep '^SLACK_CHANNEL_ID=' "$ENV_FILE" | cut -d= -f2-)
fi

dead_count=0
auth_fail_count=0
last_auth_recovery=0
last_slack_alert=0

log() {
    echo "[watchdog] $(date -u +%H:%M:%S) $*"
}

slack_alert() {
    # Send a message to Slack so users know Charlie is down.
    # Rate limited to 1 alert per 10 minutes to avoid spam.
    local msg="$1"
    local now
    now=$(date +%s)
    local time_since=$((now - last_slack_alert))

    if [ "$time_since" -lt 600 ]; then
        log "Skipping Slack alert (last sent ${time_since}s ago, min 600s)"
        return
    fi

    if [ -z "${SLACK_BOT_TOKEN:-}" ] || [ -z "${SLACK_CHANNEL_ID:-}" ]; then
        log "No Slack credentials -- cannot send alert"
        return
    fi

    local response
    response=$(curl -s -X POST "https://slack.com/api/chat.postMessage" \
        -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"${SLACK_CHANNEL_ID}\",\"text\":\"${msg}\"}" 2>&1)

    if echo "$response" | grep -q '"ok":true'; then
        log "Slack alert sent."
        last_slack_alert=$now
    else
        log "Slack alert FAILED: $response"
    fi
}

drop_alert() {
    local alert_type="$1"
    local alert_msg="$2"
    local msg_id="watchdog-${alert_type}-$(date +%s)"
    cat > "${INBOX_DIR}/${msg_id}.json" << ALERTEOF
{
  "id": "${msg_id}",
  "channel": "system",
  "user": "watchdog",
  "text": "[WATCHDOG] ${alert_msg}",
  "thread_ts": null,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
ALERTEOF
}

check_auth_failure() {
    # Capture last 50 lines of the lead pane and look for auth errors
    local scrollback
    scrollback=$(tmux capture-pane -t "${SESSION}:${WINDOW}" -p -S -50 2>/dev/null || echo "")

    if echo "$scrollback" | grep -qE '(API Error: 401|authentication_error|OAuth token has expired|Please run /login)'; then
        return 0  # auth failure detected
    fi
    return 1  # no auth failure
}

check_claude_alive() {
    local pane_pid
    pane_pid=$(tmux list-panes -t "${SESSION}:${WINDOW}" -F "#{pane_pid}" 2>/dev/null | head -1)

    if [ -z "$pane_pid" ]; then
        return 1  # pane not found
    fi

    if pgrep -P "$pane_pid" -f "claude" > /dev/null 2>&1; then
        return 0  # claude is running
    fi
    return 1  # claude not running
}

attempt_token_refresh() {
    log "Attempting token refresh..."
    if [ -x "$REFRESH_SCRIPT" ]; then
        if "$REFRESH_SCRIPT" --force 2>&1 | while read -r line; do log "  $line"; done; then
            log "Token refresh succeeded."
            return 0
        else
            log "Token refresh FAILED."
            return 1
        fi
    else
        log "Refresh script not found or not executable: $REFRESH_SCRIPT"
        return 1
    fi
}

kill_claude() {
    local pane_pid
    pane_pid=$(tmux list-panes -t "${SESSION}:${WINDOW}" -F "#{pane_pid}" 2>/dev/null | head -1)
    if [ -n "$pane_pid" ]; then
        # Kill claude processes that are children of the pane
        pkill -P "$pane_pid" -f "claude" 2>/dev/null || true
        sleep 2
        # Force kill if still alive
        pkill -9 -P "$pane_pid" -f "claude" 2>/dev/null || true
    fi
}

restart_claude() {
    log "Restarting Claude Code in ${SESSION}:${WINDOW}..."
    kill_claude
    sleep 3
    # Source bashrc to pick up CLAUDE_CODE_OAUTH_TOKEN, then launch
    tmux send-keys -t "${SESSION}:${WINDOW}" "source /root/.bashrc && cd ${PROJECT_DIR} && claude" Enter
}

log "Started. Checking ${SESSION}:${WINDOW} every ${CHECK_INTERVAL}s."
log "Auth failure detection: ENABLED"
log "Refresh script: ${REFRESH_SCRIPT}"

while true; do
    now=$(date +%s)

    # Check 1: Is Claude Code process alive?
    if check_claude_alive; then
        dead_count=0

        # Check 2: Is Claude Code hitting auth errors?
        if check_auth_failure; then
            auth_fail_count=$((auth_fail_count + 1))
            log "Auth failure detected. Count: ${auth_fail_count}/${AUTH_FAIL_THRESHOLD}"

            if [ "$auth_fail_count" -ge "$AUTH_FAIL_THRESHOLD" ]; then
                # Avoid recovery loops -- minimum 5 min between attempts
                time_since_last=$((now - last_auth_recovery))
                if [ "$time_since_last" -lt 300 ]; then
                    log "Skipping recovery -- last attempt was ${time_since_last}s ago (min 300s)"
                else
                    log "Auth failure sustained. Starting recovery..."
                    last_auth_recovery=$now

                    if attempt_token_refresh; then
                        # Token refreshed -- restart Claude Code to pick up new token
                        restart_claude
                        drop_alert "auth-recovery" "Token expired. Refresh succeeded. Claude Code restarted."
                        slack_alert "I ran into an authentication issue and had to restart. Token was refreshed automatically. Back online now."
                        log "Auth recovery complete. Claude Code restarted."
                    else
                        # Refresh failed -- alert but don't restart (pointless without valid token)
                        drop_alert "auth-dead" "Token expired and refresh FAILED. Manual re-auth required: claude auth login"
                        slack_alert "I'm offline -- my authentication token expired and automatic refresh failed. A human needs to log in and re-authenticate me. Sorry about the interruption."
                        log "CRITICAL: Token refresh failed. Manual intervention needed."
                    fi
                    auth_fail_count=0
                fi
            fi
        else
            auth_fail_count=0
        fi
    else
        auth_fail_count=0
        dead_count=$((dead_count + 1))
        log "Claude not running. Count: ${dead_count}/${DEAD_THRESHOLD}"

        if [ "$dead_count" -ge "$DEAD_THRESHOLD" ]; then
            log "Lead dead for ${DEAD_THRESHOLD} checks. Restarting..."
            restart_claude
            drop_alert "restart" "Claude Code was found dead and has been restarted. Check for unprocessed inbox messages."
            slack_alert "I went offline briefly but I'm restarting now. Should be back in a moment."
            dead_count=0
            sleep 30  # extra wait for Claude to boot
        fi
    fi

    sleep "$CHECK_INTERVAL"
done
