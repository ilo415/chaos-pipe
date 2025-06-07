#!/usr/bin/env bash

pip uninstall -y flask  # 🔥 nuke any preinstalled Flask
pip install -r requirements.txt

# Browser cache for Render
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

# Install browser engines
python -m playwright install chromium --with-deps
