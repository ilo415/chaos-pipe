#!/usr/bin/env bash
echo "🔧 Running custom build step: installing deps..."
pip install -r requirements.txt
python -m playwright install --with-deps
