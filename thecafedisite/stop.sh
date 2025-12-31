#!/bin/bash

# Kill Django dev server (port 8000)
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Kill Tailwind watch
pkill -f "tailwindcss" 2>/dev/null

# Deactivate venv if active
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null
fi

echo "Dev server and Tailwind watch stopped."
