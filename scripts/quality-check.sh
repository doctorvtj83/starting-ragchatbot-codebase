#!/bin/bash

# Comprehensive quality check script
echo "🔍 Running comprehensive quality checks..."
echo ""

# Check code formatting
echo "1. Checking code formatting..."
./scripts/check-format.sh
FORMAT_EXIT_CODE=$?

echo ""
echo "📊 Quality Check Summary:"
echo "========================"

if [ $FORMAT_EXIT_CODE -eq 0 ]; then
    echo "✅ Code formatting: PASSED"
else
    echo "❌ Code formatting: FAILED"
fi

echo ""
if [ $FORMAT_EXIT_CODE -eq 0 ]; then
    echo "🎉 All quality checks passed!"
    exit 0
else
    echo "❌ Some quality checks failed. Please fix the issues above."
    exit 1
fi