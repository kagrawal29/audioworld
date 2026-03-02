# AudioWorld Server Setup Guide

Complete rebuild guide for the AudioWorld LinkedIn outreach system. Follow this when provisioning a fresh DigitalOcean droplet or recovering from a full server wipe.

**Server:** DigitalOcean droplet, Ubuntu 24.04 LTS, 8GB RAM, 160GB disk
**Static IP:** 142.93.223.13

---

## 1. Base System

```bash
apt update && apt upgrade -y
apt install -y git python3 python3-venv python3-pip tmux xfce4 xfce4-goodies \
  tigervnc-standalone-server tigervnc-common websockify nodejs npm snapd
snap install chromium
```

## 2. VNC Server (Display :1)

### Configure VNC password
```bash
vncpasswd
# Set password: charlie1
```

### Create xstartup
```bash
mkdir -p ~/.vnc
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
startxfce4
EOF
chmod +x ~/.vnc/xstartup
```

### Create systemd service
```bash
cat > /etc/systemd/system/vncserver.service << 'EOF'
[Unit]
Description=TigerVNC Server on :1
After=syslog.target network.target

[Service]
Type=forking
User=root
ExecStartPre=/usr/bin/vncserver -kill :1 || true
ExecStart=/usr/bin/vncserver :1 -geometry 1280x720 -depth 24
ExecStop=/usr/bin/vncserver -kill :1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

## 3. noVNC (Web Access on port 6080)

### Install noVNC
```bash
git clone https://github.com/novnc/noVNC /opt/noVNC
```

### Create systemd service
```bash
cat > /etc/systemd/system/novnc.service << 'EOF'
[Unit]
Description=noVNC WebSocket Proxy
After=vncserver.service
Requires=vncserver.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/websockify --web /opt/noVNC 0.0.0.0:6080 localhost:5901
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and start both
```bash
systemctl daemon-reload
systemctl enable vncserver novnc
systemctl start vncserver && sleep 2 && systemctl start novnc
```

**Access:** `http://142.93.223.13:6080/vnc.html` (password: charlie1)

## 4. Bright Data Proxy Forwarder

Local proxy on 127.0.0.1:8888 that injects Bright Data authentication into outbound requests.

### Create proxy script
```bash
cat > /root/proxy-forwarder.py << 'PYEOF'
#!/usr/bin/env python3
"""Local proxy that forwards to Bright Data upstream with auth injected."""

import socket
import threading
import base64
import select

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8888
UPSTREAM_HOST = "brd.superproxy.io"
UPSTREAM_PORT = 33335
UPSTREAM_USER = "brd-customer-hl_e6418788-zone-isp_proxy1-country-in"
UPSTREAM_PASS = "jhh66q2vg816"

AUTH_HEADER = "Proxy-Authorization: Basic {}\r\n".format(
    base64.b64encode("{}:{}".format(UPSTREAM_USER, UPSTREAM_PASS).encode()).decode()
).encode()


def pipe(src, dst):
    try:
        while True:
            r, _, _ = select.select([src], [], [], 60)
            if not r:
                break
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except (OSError, BrokenPipeError):
        pass


def handle_client(client):
    upstream = None
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                client.close()
                return
            data += chunk

        header_end = data.index(b"\r\n\r\n")
        headers = data[:header_end]
        body = data[header_end + 4:]

        first_line_end = headers.index(b"\r\n")
        first_line = headers[:first_line_end]
        rest = headers[first_line_end + 2:]

        new_data = first_line + b"\r\n" + AUTH_HEADER + rest + b"\r\n\r\n" + body

        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(30)
        upstream.connect((UPSTREAM_HOST, UPSTREAM_PORT))
        upstream.sendall(new_data)

        if first_line.startswith(b"CONNECT"):
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                response += chunk
            client.sendall(response)

        t = threading.Thread(target=pipe, args=(upstream, client), daemon=True)
        t.start()
        pipe(client, upstream)
    except Exception:
        pass
    finally:
        for s in (client, upstream):
            if s:
                try:
                    s.close()
                except Exception:
                    pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCAL_HOST, LOCAL_PORT))
    server.listen(50)
    print("Proxy forwarder on {}:{}".format(LOCAL_HOST, LOCAL_PORT))

    while True:
        client, _ = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
PYEOF
chmod +x /root/proxy-forwarder.py
```

### Create Chromium proxy auth extension
```bash
mkdir -p /root/proxy-auth-ext

cat > /root/proxy-auth-ext/manifest.json << 'EOF'
{
  "manifest_version": 2,
  "name": "Proxy Auth",
  "version": "1.0",
  "permissions": ["webRequest", "webRequestBlocking", "<all_urls>"],
  "background": {"scripts": ["background.js"]}
}
EOF

cat > /root/proxy-auth-ext/background.js << 'EOF'
chrome.webRequest.onAuthRequired.addListener(
  function(details) {
    return {
      authCredentials: {
        username: "brd-customer-hl_e6418788-zone-isp_proxy1-country-in",
        password: "jhh66q2vg816"
      }
    };
  },
  {urls: ["<all_urls>"]},
  ["blocking"]
);
EOF
```

### Create systemd service
```bash
cat > /etc/systemd/system/proxy-forwarder.service << 'EOF'
[Unit]
Description=Bright Data Proxy Forwarder
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /root/proxy-forwarder.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable proxy-forwarder
systemctl start proxy-forwarder
```

### CRITICAL: Proxy is mandatory for LinkedIn
The server IP (142.93.223.13) is a datacenter IP. LinkedIn will flag and potentially ban the client's account if accessed directly. **Never run Chromium without the proxy flag. No exceptions.**

### Known issue: LinkedIn blocked on ISP zone
Bright Data ISP proxy zone (`isp_proxy1`) blocks LinkedIn with `policy_20052` (compliance restriction). Fix options:
1. Complete KYC at https://brightdata.com/cp/kyc
2. Create a new residential or mobile zone in Bright Data dashboard and update credentials in `/root/proxy-forwarder.py`

**Option 3 (run without proxy) is NOT acceptable.** The proxy must be fixed before any LinkedIn activity.

Test proxy general: `curl --proxy http://127.0.0.1:8888 https://lumtest.com/myip.json`
Test proxy LinkedIn: `curl --proxy http://127.0.0.1:8888 -s -o /dev/null -w "%{http_code}" https://www.linkedin.com/`

## 5. Project Setup

```bash
mkdir -p /root/Desktop
cd /root/Desktop
git clone https://github.com/kagrawal29/audioworld.git
cd audioworld
python3 -m venv .venv
source .venv/bin/activate
pip install slack-bolt slack-sdk python-dotenv certifi websockets
```

## 6. Charlie Slack Bridge

### Configure environment
```bash
cat > /root/Desktop/audioworld/charlie/.env << 'EOF'
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN
SLACK_APP_TOKEN=xapp-YOUR-APP-TOKEN
SLACK_CHANNEL_ID=YOUR-CHANNEL-ID
CHARLIE_TMUX_TARGET=%0
EOF
```

### Slack App Configuration
Create a Slack app with these settings (see `charlie/slack-manifest.json`):

**Bot scopes:** `chat:write`, `channels:history`, `groups:history`, `im:history`, `app_mentions:read`

**Event subscriptions (bot events):**
- `message.channels`
- `message.groups`
- `message.im`
- `app_mention` (CRITICAL — without this, @mentions don't create inbox files)

**Socket Mode:** Enabled (generates the `xapp-` token)

After changing event subscriptions, you MUST reinstall the app to the workspace.

### Create required directories
```bash
mkdir -p /root/Desktop/audioworld/charlie/{inbox,outbox,logs}
```

## 7. tmux Session

```bash
tmux new-session -d -s audioworld -n lead
tmux new-window -t audioworld -n charlie
```

| Pane | Window | Purpose |
|------|--------|---------|
| %0 | lead | Claude Code team lead |
| %1 | charlie | Charlie Slack bridge |

### Start Charlie in pane %1
```bash
# Use -l flag + separate Enter (Claude Code TUI paste prevention)
tmux send-keys -t audioworld:charlie -l 'cd /root/Desktop/audioworld && .venv/bin/python -m charlie.app'
sleep 0.3
tmux send-keys -t audioworld:charlie Enter
```

### Start Claude Code in pane %0
```bash
tmux send-keys -t audioworld:lead -l 'cd /root/Desktop/audioworld && claude'
sleep 0.3
tmux send-keys -t audioworld:lead Enter
```

## 8. Chromium Browser

LinkedIn session persists in the Chromium profile at `~/snap/chromium/common/chromium/Default/`.

### Launch with required flags
```bash
export DISPLAY=:1
xhost +local: 2>/dev/null
chromium-browser --no-sandbox --disable-gpu --start-maximized \
  --proxy-server=http://127.0.0.1:8888 \
  --remote-debugging-port=9222 2>/dev/null &
```

**Both flags required:**
- `--proxy-server=http://127.0.0.1:8888` — Routes through Bright Data (if proxy works for LinkedIn)
- `--remote-debugging-port=9222` — Enables CDP for Playwright/operator browser control

If proxy doesn't work for LinkedIn (see section 4 known issue), omit `--proxy-server`.

### Verify CDP
```bash
curl -s http://localhost:9222/json/version
```
Should return JSON with `webSocketDebuggerUrl`.

### LinkedIn Login
Must be done manually via VNC (`http://142.93.223.13:6080/vnc.html`). Session cookies persist in the Chromium profile across restarts.

## 9. MCP Configuration (Composio Rube)

For Google Drive/Sheets integration via `charlietheagent606@gmail.com`.

```bash
cat > /root/Desktop/audioworld/.mcp.json << 'EOF'
{
  "mcpServers": {
    "rube": {
      "type": "url",
      "url": "https://rube.app/mcp",
      "headers": {
        "Authorization": "Bearer YOUR-RUBE-JWT-TOKEN"
      }
    }
  }
}
EOF
```

Get the JWT token from https://rube.app after connecting Google Sheets and Google Drive.

**Available Google Sheets tools via Rube:**
- `GOOGLESHEETS_VALUES_GET` / `GOOGLESHEETS_VALUES_UPDATE`
- `GOOGLESHEETS_BATCH_GET` / `GOOGLESHEETS_UPDATE_VALUES_BATCH`
- `GOOGLESHEETS_GET_SPREADSHEET_INFO` / `GOOGLESHEETS_GET_SHEET_NAMES`
- `GOOGLESHEETS_SEARCH_SPREADSHEETS`

**Connected account:** `charlietheagent606@gmail.com` (Google Sheets + Gmail + Google Drive)

## 10. Claude Code Agent Teams (Experimental)

The system uses Claude Code Agent Teams for multi-agent coordination with visible tmux panes.

### Enable
Add to Claude Code settings (`~/.claude/settings.json`):
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Architecture
- **Lead (pane %0):** Orchestrates work, handles Slack messages via Charlie. Never does heavy work inline.
- **Helper teammate:** Persistent background worker for research, sheet building, spreadsheet updates. Spawned at startup.
- **Operator teammate:** LinkedIn browser operator, spawned on demand for /prep and /sprint via the `linkedin-operator` agent definition.
- **Charlie (pane %1):** Python Slack bridge (not a Claude Code agent).

### How teammates appear
With `teammateMode: "tmux"`, each teammate gets its own tmux pane. User can `ctrl+b n` to see each agent's work.

### Key rules
- Teammates coordinate via shared task list
- Teammates can message each other directly
- No nesting (teammates can't spawn their own teams)
- Lead stays responsive — all heavy work delegated to teammates

## 11. Operator Agent

Defined at `.claude/agents/linkedin-operator.md`. Controls Chromium via Playwright MCP over CDP (port 9222).

### Playwright MCP config (in agent definition)
```yaml
mcpServers:
  playwright:
    type: stdio
    command: npx
    args:
      - "@playwright/mcp@latest"
      - "--cdp-endpoint"
      - "http://localhost:9222"
      - "--snapshot-mode"
      - "none"
      - "--console-level"
      - "error"
      - "--image-responses"
      - "omit"
```

### Install Playwright dependencies
```bash
npm install -g @playwright/mcp
npx playwright install-deps chromium
```

### Operator memory
```bash
mkdir -p ~/.claude/agent-memory/linkedin-operator/
```

## 12. Network Ports

| Port | Service | Bind Address | Process |
|------|---------|--------------|---------|
| 5901 | VNC (TigerVNC) | 127.0.0.1 | Xtigervnc |
| 6080 | noVNC WebSocket | 0.0.0.0 | websockify |
| 8888 | Proxy forwarder | 127.0.0.1 | python3 |
| 9222 | Chromium CDP | 127.0.0.1 | chromium |

## 13. Scheduled Triggers

Charlie fires scheduled triggers from `charlie/schedule.json` (timezone: Asia/Kolkata):

| Time | Days | Trigger | Purpose |
|------|------|---------|---------|
| 09:30 | Mon-Fri | morning-briefing | Check if today's sheet is approved |
| 13:00 | Mon-Fri | post-sprint-summary | Summarize results if sprint ran |
| 17:00 | Friday | friday-next-week | Review next week's plan |
| 18:00 | Mon-Fri | evening-actuals | Reconcile sprint actuals |

Trigger persistence: `.scheduler-fired.json` tracks fired triggers by date+ID to prevent re-fires on restart. Delete this file to force all triggers to re-fire.

## 14. Verification Checklist (post-setup)

After completing setup, run through the startup checklist in `CLAUDE.md` (Phase 0-6):

1. Proxy listening on 8888, exit IP is Indian
2. VNC and noVNC active
3. Chromium with CDP on 9222
4. Charlie connected to Slack (Socket Mode)
5. Outbox delivery working
6. MCP (Rube) config present
7. Operator agent definition + field manual present
8. LinkedIn logged in (manual via VNC)
9. Slack E2E test (user @mentions Charlie, inbox file appears)

## 15. File Structure

```
/root/Desktop/audioworld/
├── CLAUDE.md                          # Operational playbook (loaded every session)
├── SETUP.md                           # This file (rebuild guide)
├── AudioWorld_March_2026_*.xlsx       # Local spreadsheet backup
├── .mcp.json                          # MCP server config (Composio Rube)
├── .claude/
│   ├── agents/
│   │   └── linkedin-operator.md       # Operator agent definition
│   ├── skills/
│   │   ├── prep/SKILL.md              # /prep skill
│   │   ├── review/SKILL.md            # /review skill
│   │   ├── sprint/SKILL.md            # /sprint skill
│   │   └── status/SKILL.md            # /status skill
│   └── settings.local.json            # Permission whitelist
├── charlie/
│   ├── app.py                         # Slack bridge (main)
│   ├── bridge.py                      # File I/O + tmux integration
│   ├── config.py                      # Configuration constants
│   ├── CHARACTER.md                   # Charlie persona + voice rules
│   ├── .env                           # Slack tokens + tmux target
│   ├── schedule.json                  # Scheduled trigger definitions
│   ├── slack-manifest.json            # Slack app config reference
│   ├── .scheduler-fired.json          # Trigger dedup state
│   ├── inbox/                         # Incoming Slack messages (JSON)
│   ├── outbox/                        # Outgoing Slack messages (JSON)
│   └── logs/                          # Daily JSONL exchange logs
├── sprint-prep/
│   ├── field-manual.md                # Operator playbook (pacing, limits, selectors)
│   └── YYYY-MM-DD-segment.md          # Execution sheets
/root/
├── proxy-forwarder.py                 # Bright Data proxy script
├── proxy-auth-ext/                    # Chromium proxy auth extension
│   ├── manifest.json
│   └── background.js
├── .vnc/xstartup                      # VNC desktop startup
├── snap/chromium/common/chromium/     # Chromium profile (LinkedIn session)
/etc/systemd/system/
├── vncserver.service                  # TigerVNC on :1
├── novnc.service                      # noVNC on :6080
├── proxy-forwarder.service            # Bright Data proxy on :8888
```
