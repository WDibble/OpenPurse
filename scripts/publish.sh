#!/bin/bash

# OpenPurse Release Script
# This script cleans the build directory, builds the package, and uploads it to PyPI using credentials from .env

# Exit immediately if a command exits with a non-zero status
set -e

# Change to the root directory of the project
cd "$(dirname "$0")/.."

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found. Please create one based on .env.example."
    exit 1
fi

# Check if TWINE_PASSWORD is set
if [ -z "$TWINE_PASSWORD" ]; then
    echo "Error: TWINE_PASSWORD is not set in .env. This should be your PyPI API token."
    exit 1
fi

# 1. Clean old builds
echo "Cleaning dist/ directory..."
rm -rf dist/*

# 2. Build the package
echo "Building package..."
python3 -m build

# 3. Upload to PyPI
# We use TWINE_USERNAME=__token__ and TWINE_PASSWORD as the API token
echo "Uploading to PyPI..."
export TWINE_USERNAME=__token__
python3 -m twine upload --skip-existing dist/*

echo "Successfully published to PyPI!"
