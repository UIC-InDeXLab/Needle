#!/bin/bash

# Exit immediately if any command fails
set -e

# echo "=== Checking for Homebrew installation ==="
# if ! command -v brew &> /dev/null; then
#   echo "Homebrew not found. Installing..."
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
# else
#   echo "Homebrew is already installed."
# fi

# echo "=== Installing Python (via Homebrew if needed) ==="
# if ! brew list python &> /dev/null; then
#   brew install python
# else
#   echo "Python is already installed via Homebrew."
# fi
# export PATH="$(brew --prefix)/opt/python/libexec/bin:$PATH"

echo "=== Downloading and extracting repositories ==="
wget https://github.com/UIC-InDeXLab/ImageGeneratorsHub/archive/refs/heads/main.zip -O imagehub.zip
unzip imagehub.zip && rm imagehub.zip
wget https://github.com/UIC-InDeXLab/Needle/archive/refs/heads/main.zip -O needle.zip
unzip needle.zip && rm needle.zip

echo "=== Creating virtual environment and installing dependencies ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r ImageGeneratorsHub-main/requirements.txt
pip install -r Needle-main/backend/requirements.txt


echo "=== Setting up Docker containers ==="
docker compose -f Needle-main/docker/docker-compose.cpu.yaml up -d

echo "=== Installing PostgreSQL and setting up database ==="
brew install postgresql@14
brew services start postgresql@14
export PATH="/usr/local/opt/postgresql@14/bin:$PATH"

Create user and database (idempotent)
createuser myuser || echo "User 'myuser' already exists"
psql -c "ALTER USER myuser WITH PASSWORD 'mypassword';" || true
createdb -O myuser mydb || echo "Database 'mydb' already exists"
pg_isready -U myuser -d mydb

# echo "=== Starting ImageGeneratorsHub (port 8001) ==="
# uvicorn main:app --app-dir ./ImageGeneratorsHub-main --host 0.0.0.0 --port 8001 &
# IMG_PID=$!

# echo "=== Starting Needle Backend (port 8000) ==="

# echo "Choose configuration mode for Needle backend:"
# select config_mode in "fast" "balanced" "accurate"; do
#   case $config_mode in
#     fast|balanced|accurate)
#       export SERVICE__CONFIG_DIR_PATH="Needle-main/configs/$config_mode"
#       break
#       ;;
#     *)
#       echo "Invalid selection. Please choose 1 (fast), 2 (balanced), or 3 (accurate)."
#       ;;
#   esac
# done

# uvicorn main:app --app-dir ./Needle-main/backend/ --host 0.0.0.0 --port 8000 &
# NEEDLE_PID=$!

# # Trap CTRL+C to cleanly stop both apps
# trap "echo -e '\nStopping servers...'; kill $IMG_PID $NEEDLE_PID; exit" SIGINT

# # Wait for both to exit (blocks script)
# wait