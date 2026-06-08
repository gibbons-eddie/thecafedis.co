#!/bin/bash

cd "$(dirname "$0")"

# Activate virtual environment
source ../.venv/bin/activate

# Start Tailwind watch in background
npx tailwindcss -i styles/styles.css -o static/dist/styles.css --watch &
TAILWIND_PID=$!

# Trap to kill Tailwind when script exits
trap "kill $TAILWIND_PID 2>/dev/null" EXIT

echo "Tailwind watch started (PID: $TAILWIND_PID)"

if [ "$1" = "--mobile" ]; then
  export DEBUG=true
  LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
  echo "Starting Django dev server (mobile mode)..."
  echo "Local:  http://localhost:8000"
  echo "Phone:  http://${LAN_IP}:8000"
  echo ""
  python3 manage.py runserver 0.0.0.0:8000
else
  echo "Starting Django dev server..."
  echo ""
  python3 manage.py runserver
fi
