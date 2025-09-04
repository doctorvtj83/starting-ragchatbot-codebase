#!/bin/bash

# Check code formatting without modifying files
echo "🔍 Checking code formatting..."
uv run black --check --diff .

if [ $? -eq 0 ]; then
    echo "✅ Code formatting is consistent!"
else
    echo "❌ Code formatting issues found. Run './scripts/format.sh' to fix them."
    exit 1
fi