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

# 0. Auto-increment Patch Version
CURRENT_VERSION=$(grep -m 1 'version =' pyproject.toml | tr -d '"' | tr -d "'" | awk '{print $3}')
NEW_VERSION=$(python3 -c "v = '$CURRENT_VERSION'.split('.'); v[-1] = str(int(v[-1]) + 1); print('.'.join(v))")

echo "Bumping version: $CURRENT_VERSION -> $NEW_VERSION"
# Update pyproject.toml (using a temp file for macOS compatibility with sed)
sed "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml

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
