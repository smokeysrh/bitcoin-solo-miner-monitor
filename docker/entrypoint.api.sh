#!/bin/bash
set -e

# InfluxDB is no longer required - removed dependency wait

# Initialize the database if needed
python src/tools/init_db.py

# Execute the command
exec "$@"