#!/usr/bin/env python3
"""
Bitcoin Solo Miner Monitoring App - Startup Script

This script starts the application from the project root directory.
"""

import sys
import os
import asyncio

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main application
from src.main import main

if __name__ == "__main__":
    asyncio.run(main())