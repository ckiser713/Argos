#!/bin/bash
# Test environment variable loading

echo "Testing environment variable loading..."
echo ""

# Test if .env file exists
if [ -f ".env" ]; then
    echo "✓ .env file exists"
else
    echo "❌ .env file not found"
    exit 1
fi

# Test docker-compose config
echo ""
echo "Testing docker-compose config..."
docker compose -f ops/docker-compose.strix.yml config --quiet
if [ $? -eq 0 ]; then
    echo "✓ docker-compose config is valid"
else
    echo "❌ docker-compose config has errors"
    exit 1
fi

echo ""
echo "Environment variables from .env:"
echo "N8N_PASSWORD: ${N8N_PASSWORD:-NOT_SET}"
echo "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-NOT_SET}"
echo "CORTEX_VLLM_IMAGE: ${CORTEX_VLLM_IMAGE:-NOT_SET}"

echo ""
echo "Test complete!"