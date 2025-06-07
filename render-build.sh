#!/usr/bin/env bash

pip install -r requirements.txt

# Set Playwright cache location (where Render won't wipe it)
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

# Install the browser deps where Playwright expects them
python -m playwright install chromium --with-deps
