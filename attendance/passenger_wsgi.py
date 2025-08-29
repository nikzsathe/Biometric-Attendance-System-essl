#!/usr/bin/env python3
"""
Passenger WSGI file for cPanel Python App deployment
This file tells the server how to run your Flask application
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the Flask app
from web_app import app, setup_db

# Setup database
setup_db()

# Create application object for Passenger
application = app

# For debugging (optional)
if __name__ == '__main__':
    app.run()

