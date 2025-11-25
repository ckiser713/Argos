#!/bin/bash
set -e

echo "--- Checking Development Environment ---"

# Check for Docker
if ! command -v docker &> /dev/null
then
    echo "❌ Docker could not be found. Please install Docker."
    exit 1
fi
echo "✅ Docker found"

# Check for Docker Compose
if command -v docker-compose &> /dev/null
then
    echo "✅ docker-compose (V1) found"
elif docker compose version &> /dev/null
then
    echo "✅ docker compose (V2) found"
else
    echo "❌ Docker Compose could not be found. Please install docker-compose or the 'compose' docker plugin."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 could not be found. Please install Python 3.11+."
    exit 1
fi
echo "✅ Python 3 found"

# Check for Node
if ! command -v node &> /dev/null
then
    echo "❌ Node.js could not be found. Please install Node.js 18+."
    exit 1
fi
echo "✅ Node.js found"


echo "--- Environment check passed! ---"
