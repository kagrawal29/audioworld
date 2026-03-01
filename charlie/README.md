# Charlie — Slack Bridge for AudioWorld

Relays messages between Slack and the Claude Code team lead running in tmux.

## Quick Start

### 1. Start tmux session

```bash
tmux new-session -s audioworld
```

### 2. Split into two panes

```bash
# Inside tmux, press:
Ctrl+B then %
```

This gives you two side-by-side panes: left (lead) and right (operator).

### 3. Start Charlie in a separate terminal

Open a **new terminal window** (outside tmux):

```bash
cd ~/Desktop/Seed\ Forth/audioworld
python3 -m charlie.app
```

You should see:
```
Starting Charlie — Slack bridge for AudioWorld
⚡️ Bolt app is running!
```

### 4. Start the lead in tmux

Click into the **left tmux pane** and start Claude Code:

```bash
cd ~/Desktop/Seed\ Forth/audioworld
claude
```

The lead will now receive Slack messages as tmux input automatically.

### 5. Test it

Send a message in the `#linkedin` Slack channel. You should see:
- Charlie replies "Got it, processing..." in Slack
- The lead's tmux pane receives a nudge to process the inbox file

## How It Works

```
Slack message → charlie/inbox/{id}.json → tmux send-keys → Lead processes
Lead writes → charlie/outbox/{id}.json → Charlie posts to Slack
```

## tmux Navigation

| Keys | Action |
|------|--------|
| `Ctrl+B` then arrow keys | Switch between panes |
| `Ctrl+B` then `z` | Zoom/unzoom current pane |
| `Ctrl+B` then `%` | Split vertically |
| `Ctrl+B` then `"` | Split horizontally |
| `Ctrl+B` then `d` | Detach (session keeps running) |
| `tmux attach -t audioworld` | Reattach later |

## Configuration

Edit `charlie/.env`:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL_ID=C...
CHARLIE_TMUX_TARGET=audioworld:0.0
```

`CHARLIE_TMUX_TARGET` format: `session:window.pane` — default `audioworld:0.0` points to the first pane of the first window.

## Troubleshooting

**Charlie starts but Slack messages don't arrive:**
- Ensure the bot is invited to the channel (`/invite @Charlie`)
- Check Event Subscriptions include `message.groups` (for private channels)

**"Got it, processing..." but lead doesn't react:**
- Verify tmux session is named `audioworld`: `tmux list-sessions`
- Check the lead is in pane 0.0: `tmux list-panes -t audioworld`

**SSL errors on macOS:**
- Already handled in `app.py` via `certifi`. If issues persist: `pip3 install --upgrade certifi`
