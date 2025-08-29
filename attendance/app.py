#!/usr/bin/env python3
"""
Production Attendance System for Cloud Deployment
This file is optimized for cPanel Python App deployment
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the main application
from web_app import app, setup_db

# Production configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
app.config['DEBUG'] = False

# Database setup
if __name__ == '__main__':
    # Setup database
    setup_db()
    
    # Get port from environment variable (cPanel sets this)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=port,
        debug=False
    )

