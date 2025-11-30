#!/bin/bash
set -e
cd /home/nexus/Argos_Chatgpt/backend
export CORTEX_ENV=strix
export CORTEX_SKIP_AUTH=false
export IN_NIX_SHELL=1
export CORTEX_AUTH_SECRET=3bfcee0b6c5e94bc6754e0da4a4a56970b912ce01f633e880a603de3e073396b
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

