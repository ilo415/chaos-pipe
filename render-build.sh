#!/usr/bin/env bash

# Uninstall any rogue flask versions (Render caches weird sometimes)
pip uninstall -y flask

# Install deps clean
pip install -r requirements.txt

# Render-safe playwright browser path
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

# Install Chromium where Playwright expects it
python -m playwright install chromium --with-deps
