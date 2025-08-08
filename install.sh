#!/bin/bash

set -e
echo "=== Downloading and extracting repositories ==="
wget https://github.com/UIC-InDeXLab/ImageGeneratorsHub/archive/refs/heads/main.zip -O imagehub.zip
unzip imagehub.zip && rm imagehub.zip
wget https://github.com/UIC-InDeXLab/Needle/archive/refs/heads/linh.zip -O needle.zip
unzip needle.zip && rm needle.zip
mv ImageGeneratorsHub-main Needle-linh/

echo "=== Creating virtual environment and installing dependencies ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r ImageGeneratorsHub-main/requirements.txt
pip install -r Needle-linh/backend/requirements.txt


echo "=== Setting up Docker containers ==="
docker compose -f Needle-linh/docker/docker-compose.cpu.yaml up -d

echo "=== Installing PostgreSQL and setting up database ==="
brew install postgresql@14
brew services start postgresql@14
export PATH="/usr/local/opt/postgresql@14/bin:$PATH"

# Create user and database (idempotent)
createuser myuser || echo "User 'myuser' already exists"
psql -c "ALTER USER myuser WITH PASSWORD 'mypassword';" || true
createdb -O myuser mydb || echo "Database 'mydb' already exists"
pg_isready -U myuser -d mydb
