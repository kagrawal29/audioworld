#!/bin/bash
# Charlie Server Setup - DigitalOcean Ubuntu 24.04
# Run as root: bash server-setup.sh

set -e

echo "=== Installing Node.js 23.x ==="
curl -fsSL https://raw.githubusercontent.com/nodesource/distributions/main/deb/setup_23.x | bash -

echo "=== Installing system packages ==="
apt-get update
apt-get install -y nodejs python3 python3-pip python3-venv tmux git chromium-browser

echo "=== Installing Claude Code ==="
npm install -g @anthropic-ai/claude-code

echo "=== Done. All installed. ==="
node --version
python3 --version
claude --version 2>/dev/null || echo "Claude Code installed (run 'claude' to authenticate)"
