#!/bin/bash
# Run invoker integration tests
#
# Usage:
#   ./run_tests.sh           # Run all tests
#   ./run_tests.sh -v        # Run with verbose output
#   ./run_tests.sh -k init   # Run only tests matching 'init'

set -e

# Check if pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "pytest is not installed. Installing test dependencies..."
    pip install -r requirements-dev.txt
fi

# Run pytest with any additional arguments
echo "Running invoker integration tests..."
python -m pytest "$@"

