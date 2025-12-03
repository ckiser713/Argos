#!/usr/bin/env python3
"""Initialize database schema for staging deployment."""
import os
import sys

# Set environment variables BEFORE any imports
os.environ['CORTEX_ENV'] = 'strix'
if 'CORTEX_AUTH_SECRET' not in os.environ:
    import secrets
    os.environ['CORTEX_AUTH_SECRET'] = secrets.token_hex(32)

# Now import and initialize
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import create_app

app = create_app()
print("✓ Database schema initialized successfully")





