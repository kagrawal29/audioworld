#!/usr/bin/env bash
# refresh-token.sh -- Proactively refresh Claude Code OAuth tokens before expiry.
# Runs as a systemd timer (every 30 min). Reads .credentials.json, checks
# expiresAt, and uses the refresh_token to get a new access_token if expiring
# within 1 hour.
#
# Usage: ./refresh-token.sh [--force]
#   --force: refresh even if token hasn't expired yet

set -euo pipefail

CREDS_FILE="${CLAUDE_CREDENTIALS_FILE:-/root/.claude/.credentials.json}"
TOKEN_URL="https://platform.claude.com/v1/oauth/token"
CLIENT_ID="9d1c250a-e61b-44d9-88ed-5944d1962f5e"
REFRESH_WINDOW_MS=$((60 * 60 * 1000))  # 1 hour before expiry
RETRY_DELAY=30
MAX_RETRIES=3

log() {
    echo "[refresh-token] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"
}

die() {
    log "FATAL: $*"
    exit 1
}

# Check dependencies
command -v curl >/dev/null 2>&1 || die "curl not found"
command -v python3 >/dev/null 2>&1 || die "python3 not found"

# Read credentials
[ -f "$CREDS_FILE" ] || die "Credentials file not found: $CREDS_FILE"

read_cred() {
    python3 -c "
import json, sys
with open('$CREDS_FILE') as f:
    d = json.load(f)
oauth = d.get('claudeAiOauth', {})
print(oauth.get('$1', ''))
"
}

REFRESH_TOKEN=$(read_cred refreshToken)
ACCESS_TOKEN=$(read_cred accessToken)
EXPIRES_AT=$(read_cred expiresAt)

[ -n "$REFRESH_TOKEN" ] || die "No refreshToken in credentials file"
[ -n "$EXPIRES_AT" ] || die "No expiresAt in credentials file"

# Check if refresh is needed
FORCE="${1:-}"
NOW_MS=$(python3 -c "import time; print(int(time.time() * 1000))")
EXPIRES_AT_INT=$(python3 -c "print(int($EXPIRES_AT))")
TIME_LEFT_MS=$((EXPIRES_AT_INT - NOW_MS))
TIME_LEFT_MIN=$((TIME_LEFT_MS / 60000))

if [ "$FORCE" != "--force" ] && [ "$TIME_LEFT_MS" -gt "$REFRESH_WINDOW_MS" ]; then
    log "Token still valid for ${TIME_LEFT_MIN} minutes. No refresh needed."
    exit 0
fi

if [ "$TIME_LEFT_MS" -le 0 ]; then
    log "Token EXPIRED ${TIME_LEFT_MIN#-} minutes ago. Attempting refresh..."
else
    log "Token expires in ${TIME_LEFT_MIN} minutes. Refreshing proactively..."
fi

# Attempt refresh with retries
for attempt in $(seq 1 $MAX_RETRIES); do
    log "Refresh attempt $attempt/$MAX_RETRIES..."

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$TOKEN_URL" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=refresh_token&refresh_token=${REFRESH_TOKEN}&client_id=${CLIENT_ID}" \
        2>&1)

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        # Parse new tokens from response
        NEW_ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")
        NEW_REFRESH_TOKEN=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('refresh_token',''))")
        EXPIRES_IN=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('expires_in', 0))")

        [ -n "$NEW_ACCESS_TOKEN" ] || { log "ERROR: Got 200 but no access_token in response"; continue; }

        # Calculate new expiresAt
        NEW_EXPIRES_AT=$(python3 -c "import time; print(int((time.time() + $EXPIRES_IN) * 1000))")
        NEW_EXPIRES_HUMAN=$(python3 -c "import datetime; print(datetime.datetime.utcfromtimestamp($NEW_EXPIRES_AT / 1000).strftime('%Y-%m-%d %H:%M:%S UTC'))")

        # Use the new refresh token if provided, otherwise keep the old one
        FINAL_REFRESH="${NEW_REFRESH_TOKEN:-$REFRESH_TOKEN}"

        # Read existing file to preserve other fields
        python3 -c "
import json

with open('$CREDS_FILE') as f:
    creds = json.load(f)

oauth = creds.get('claudeAiOauth', {})
oauth['accessToken'] = '$NEW_ACCESS_TOKEN'
oauth['refreshToken'] = '$FINAL_REFRESH'
oauth['expiresAt'] = $NEW_EXPIRES_AT
creds['claudeAiOauth'] = oauth

with open('$CREDS_FILE', 'w') as f:
    json.dump(creds, f)
"

        log "SUCCESS: Token refreshed. New expiry: $NEW_EXPIRES_HUMAN"
        log "Expires in: $((EXPIRES_IN / 60)) minutes"
        exit 0
    fi

    if [ "$HTTP_CODE" = "429" ]; then
        log "Rate limited (429). Waiting ${RETRY_DELAY}s before retry..."
        sleep "$RETRY_DELAY"
        RETRY_DELAY=$((RETRY_DELAY * 2))
        continue
    fi

    if [ "$HTTP_CODE" = "400" ]; then
        # Check if refresh token is invalid/revoked
        ERROR_TYPE=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',{}).get('type','') if isinstance(d.get('error'), dict) else d.get('error',''))" 2>/dev/null || echo "unknown")
        log "ERROR: Bad request (400). Error type: $ERROR_TYPE"
        log "Response: $BODY"
        die "Refresh token may be invalid or revoked. Manual re-auth required."
    fi

    log "ERROR: HTTP $HTTP_CODE. Response: $BODY"
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        log "Retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
        RETRY_DELAY=$((RETRY_DELAY * 2))
    fi
done

die "All $MAX_RETRIES refresh attempts failed. Manual intervention required."
