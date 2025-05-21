#!/bin/sh
set -e

LOG_DIR="/app/apps/etl_app/logs"

# Create the directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Fix ownership
chown -R appuser:appgroup "$LOG_DIR" || echo "Warning: could not chown logs"

# Set group write permission and sticky bit (if needed)
chmod -R ug+rw "$LOG_DIR"
chmod g+s "$LOG_DIR"  # Ensures new files inherit group

# Run passed command
exec "$@"