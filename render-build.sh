#!/usr/bin/env bash

# Install Python deps
pip install -r requirements.txt

# Install Playwright deps + browsers, without sudo
python -m playwright install --with-deps || true
