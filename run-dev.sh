#!/bin/bash

# Update and install required services
echo "Updating system and installing Redis and PostgreSQL..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y redis postgresql postgresql-contrib python3-venv python3-pip

# Start Redis service
echo "Starting Redis service..."
sudo systemctl enable redis
sudo systemctl start redis

# Start PostgreSQL service
echo "Starting PostgreSQL service..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Set up PostgreSQL (adjust username and database as needed)
echo "Configuring PostgreSQL (default user: postgres)..."
sudo -u postgres createuser --interactive
sudo -u postgres createdb goodbites  # Replace 'mydatabase' with your desired database name

# Activate Python virtual environment
echo "Setting up and activating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
echo "Installing required Python packages for Celery..."
pip install celery flower

# Run Celery worker
echo "Starting Celery Worker..."
gnome-terminal -- bash -c "source venv/bin/activate && celery -A config.celery worker --loglevel=INFO; exec bash"

# Run Celery Flower
echo "Starting Celery Flower..."
gnome-terminal -- bash -c "source venv/bin/activate && celery -A config.celery flower; exec bash"

# Run Celery Beat
echo "Starting Celery Beat..."
gnome-terminal -- bash -c "source venv/bin/activate && celery -A config.celery beat --loglevel=INFO; exec bash"

# Launch Visual Studio Code
echo "Launching Visual Studio Code..."
gnome-terminal -- bash -c "source venv/bin/activate && code .; exec bash"

echo "All tasks completed!"
