#!/bin/bash
# Setup PostgreSQL 16 with pgvector for Argos
set -e

echo "=== PostgreSQL Setup for Argos ==="

# Check if running in Nix shell
if [ -z "$IN_NIX_SHELL" ]; then
    echo "Please run this script inside 'nix develop' environment"
    echo "Usage: nix develop --command ./ops/setup-postgres.sh"
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "PostgreSQL is not running. Starting it..."

    # Try to start PostgreSQL if it's available as a service
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl start postgresql 2>/dev/null || true
    fi

    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to start..."
    for i in {1..30}; do
        if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            echo "✅ PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ PostgreSQL failed to start after 30 attempts"
            exit 1
        fi
        echo "  Waiting... ($i/30)"
        sleep 2
    done
else
    echo "✅ PostgreSQL is already running"
fi

# Create database and user if they don't exist
echo ""
echo "Setting up database and user..."
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'argos'" | grep -q 1 || \
sudo -u postgres createdb argos

sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'argos'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER argos WITH PASSWORD 'argos';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE argos TO argos;"

# Enable pgvector extension
echo ""
echo "Setting up pgvector extension..."
sudo -u postgres psql -d argos -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
sudo -u postgres psql -d argos -c "CREATE EXTENSION IF NOT EXISTS uuid_ossp;"

# Verify extensions
echo ""
echo "Verifying extensions..."
sudo -u postgres psql -d argos -c "SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name IN ('pgvector', 'uuid_ossp');"

# Test connection
echo ""
echo "Testing database connection..."
PGPASSWORD=argos psql -h localhost -p 5432 -U argos -d argos -c "SELECT version();"
PGPASSWORD=argos psql -h localhost -p 5432 -U argos -d argos -c "SELECT * FROM pg_extension WHERE extname = 'pgvector';"

echo ""
echo "✅ PostgreSQL setup complete!"
echo ""
echo "Database: postgresql://argos:argos@localhost:5432/argos"
echo ""
echo "Next steps:"
echo "1. Run database migrations: ./ops/init-db.sh"
echo "2. Start the backend: cd backend && source .venv/bin/activate && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"