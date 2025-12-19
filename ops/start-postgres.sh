#!/bin/bash
# Start PostgreSQL 16 with pgvector manually

set -e

echo "=== Starting PostgreSQL 16 with pgvector ==="

# Check if PostgreSQL is already running
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "✅ PostgreSQL is already running"
else
    echo "PostgreSQL not running, attempting to start..."

    # Try systemctl first
    if command -v systemctl >/dev/null 2>&1; then
        echo "Trying systemctl..."
        sudo systemctl start postgresql 2>/dev/null || true
        sleep 3
    fi

    # Check again
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "✅ PostgreSQL started successfully"
    else
        echo "❌ Could not start PostgreSQL with systemctl"
        echo ""
        echo "Manual start options:"
        echo "1. Install PostgreSQL: sudo apt install postgresql-16 postgresql-16-pgvector"
        echo "2. Start service: sudo systemctl start postgresql"
        echo "3. Or run: sudo -u postgres /usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/16/main -c config_file=/etc/postgresql/16/main/postgresql.conf"
        exit 1
    fi
fi

# Setup database and extensions
echo ""
echo "Setting up database and extensions..."

# Create database and user
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'argos'" 2>/dev/null | grep -q 1 || \
sudo -u postgres createdb argos

sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'argos'" 2>/dev/null | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER argos WITH PASSWORD 'argos';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE argos TO argos;"

# Enable extensions
echo "Enabling pgvector extension..."
sudo -u postgres psql -d argos -c "CREATE EXTENSION IF NOT EXISTS pgvector;" 2>/dev/null || \
echo "⚠️ pgvector extension not available - you may need to install postgresql-16-pgvector"

sudo -u postgres psql -d argos -c "CREATE EXTENSION IF NOT EXISTS uuid_ossp;"

# Test connection
echo ""
echo "Testing database connection..."
PGPASSWORD=argos psql -h localhost -p 5432 -U argos -d argos -c "SELECT version();" >/dev/null && \
echo "✅ Database connection successful"

echo ""
echo "Database setup complete!"
echo "Connection string: postgresql://argos:argos@localhost:5432/argos"
echo ""
echo "Available extensions:"
sudo -u postgres psql -d argos -c "SELECT name FROM pg_available_extensions WHERE name IN ('pgvector', 'uuid_ossp');"