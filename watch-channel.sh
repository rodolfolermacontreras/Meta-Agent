#!/bin/bash
# watch-channel.sh
# Watches teamates.md for changes and alerts you when the DEV agent posts.
# Works in Git Bash / WSL / any Unix shell on Windows.
#
# Usage:
#   cd /c/Training/Microsoft/Copilot/multi-agent
#   bash watch-channel.sh

WATCH_FILE="$(dirname "$0")/teamates.md"
CHECK_EVERY=300   # seconds (5 minutes)
LAST_HASH=""

echo ""
echo "=========================================="
echo "  Meta-Agent Communication Watcher"
echo "  Watching: teamates.md"
echo "  Interval: every ${CHECK_EVERY}s (5 min)"
echo "  Press Ctrl+C to stop."
echo "=========================================="
echo ""

if [ ! -f "$WATCH_FILE" ]; then
    echo "[ERROR] File not found: $WATCH_FILE"
    exit 1
fi

hash_file() {
    if command -v md5sum &>/dev/null; then
        md5sum "$1" | cut -d' ' -f1
    else
        md5 -q "$1" 2>/dev/null || shasum "$1" | cut -d' ' -f1
    fi
}

LAST_HASH=$(hash_file "$WATCH_FILE")
echo "[$(date '+%H:%M:%S')] Started. Baseline captured."

while true; do
    sleep "$CHECK_EVERY"

    CURRENT_HASH=$(hash_file "$WATCH_FILE")

    if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
        LAST_HASH="$CURRENT_HASH"

        echo ""
        echo "=========================================="
        echo "  NEW MESSAGE in teamates.md!"
        echo "  $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=========================================="
        tail -20 "$WATCH_FILE"
        echo "=========================================="
        echo ""
        echo "[ACTION] Go to Claude Code and type:"
        echo "  'Check teamates.md for new messages and respond'"
        echo ""

        # Windows toast via PowerShell (works in Git Bash)
        powershell.exe -Command "
            \$notify = New-Object -ComObject WScript.Shell
            \$notify.Popup('New message in teamates.md — check your terminal!', 8, 'Meta-Agent Update', 64)
        " 2>/dev/null &
    else
        echo "[$(date '+%H:%M:%S')] No changes."
    fi
done
