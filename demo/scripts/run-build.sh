#!/bin/bash
# Quick script to run the sample queries builder

echo "🔧 Building sample-queries.json from Needle API..."
echo "Make sure your Needle backend is running on http://127.0.0.1:8000"
echo ""

cd "$(dirname "$0")/.."
python3 scripts/build-sample-queries.py
