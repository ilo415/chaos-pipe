#!/usr/bin/env bash

pip install -r requirements.txt

# Install the Playwright browsers
python -m playwright install --with-deps
