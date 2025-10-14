#!/usr/bin/env bash
set -e

# Ensure Python and pip are available. If not, raise an error.
if ! command -v python3 &>/dev/null; then
  echo "Python3 not found. Please install Python3."
  exit 1
fi

if ! command -v pip3 &>/dev/null; then
  echo "pip3 not found. Please install pip."
  exit 1
fi

# Create a temporary build environment
python3 -m venv build_env
source build_env/bin/activate

# Install dependencies and PyInstaller
pip install -r requirements.txt

# Assuming needlectl.py is in the current directory
pyinstaller --add-data "tui/styles/base.css:tui/styles" --onefile needlectl.py --collect-submodules shellingham

# Move the binary to system-wide location

# Cleanup
deactivate
rm -rf build_env build __pycache__ needlectl.spec

echo "needlectl successfully built as a standalone binary."
