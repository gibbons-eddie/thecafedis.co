#!/bin/bash

cd "$(dirname "$0")"

# Activate virtual environment
source ../.venv/bin/activate

# Start Tailwind watch in background
npx tailwindcss -i static/src/styles.css -o static/dist/styles.css --watch &
TAILWIND_PID=$!

# Trap to kill Tailwind when script exits
trap "kill $TAILWIND_PID 2>/dev/null" EXIT

echo "Tailwind watch started (PID: $TAILWIND_PID)"
echo "Starting Django dev server..."
echo ""

# Start Django dev server (foreground)
python3 manage.py runserver
