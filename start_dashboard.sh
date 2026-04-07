#!/bin/bash
# start_dashboard.sh — Start the financial dashboard in a persistent tmux session.
#
# USAGE:
#   bash start_dashboard.sh          # use cached data (fast)
#   bash start_dashboard.sh --refresh # pull fresh data from YNAB
#
# FIRST TIME SETUP (run once if tmux is not installed):
#   sudo apt install tmux
#
# TO REATTACH after disconnect or closing VS Code:
#   tmux attach -t dashboard
#
# TO STOP THE DASHBOARD:
#   tmux attach -t dashboard
#   then press Ctrl+C to stop Streamlit, then type: exit

SESSION="dashboard"
cd "$(dirname "$0")"

# Build the Streamlit command based on optional --refresh flag
CMD=".venv/bin/python -m streamlit run financial_dashboard.py"
if [[ "$1" == "--refresh" ]]; then
    CMD="$CMD -- --refresh-data"
    echo "Starting dashboard with fresh YNAB data..."
else
    echo "Starting dashboard with cached data..."
fi

# If the session already exists, just reattach to it
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Dashboard already running. Reattaching (restart not triggered)."
    echo "To restart with different data, stop it first (Ctrl+C inside tmux), then re-run this script."
    tmux attach -t "$SESSION"
    exit 0
fi

# Start a new tmux session and run Streamlit inside it
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux send-keys -t "$SESSION" "$CMD" Enter

echo "Dashboard started. Reattach anytime with: tmux attach -t $SESSION"
echo "Check the sidebar for the URL to open in your browser."
tmux attach -t "$SESSION"
