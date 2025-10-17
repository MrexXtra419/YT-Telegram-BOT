#!/bin/bash
set -e

# Install ffmpeg if not installed
if ! command -v ffmpeg &> /dev/null; then
  echo "🔧 Installing ffmpeg..."
  apt-get update -y
  apt-get install -y ffmpeg
fi

echo "🚀 Starting Telegram Bot..."
python3 main.py
