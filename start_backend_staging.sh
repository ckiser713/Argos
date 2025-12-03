#!/bin/bash
set -e
cd /home/nexus/Argos_Chatgpt/backend
# Export environment variables FIRST - before any Python imports
export CORTEX_ENV=strix
export CORTEX_SKIP_AUTH=false
export IN_NIX_SHELL=1
export CORTEX_AUTH_SECRET=3bfcee0b6c5e94bc6754e0da4a4a56970b912ce01f633e880a603de3e073396b

# Clear any cached Settings instances by clearing the lru_cache
# This ensures Settings() reads fresh environment variables
python3 << 'PYTHON_SCRIPT'
import os
os.environ['CORTEX_ENV'] = 'strix'
os.environ['CORTEX_SKIP_AUTH'] = 'false'
os.environ['CORTEX_AUTH_SECRET'] = '3bfcee0b6c5e94bc6754e0da4a4a56970b912ce01f633e880a603de3e073396b'
# Clear cache before importing
import sys
if 'app.config' in sys.modules:
    from app.config import get_settings
    get_settings.cache_clear()
PYTHON_SCRIPT

# Verify environment variables are set
echo "Environment check:" >&2
echo "  CORTEX_ENV=$CORTEX_ENV" >&2
echo "  CORTEX_SKIP_AUTH=$CORTEX_SKIP_AUTH" >&2
echo "  CORTEX_AUTH_SECRET set: $([ -n "$CORTEX_AUTH_SECRET" ] && echo "yes" || echo "no")" >&2

exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

