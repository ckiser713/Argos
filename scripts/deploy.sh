#!/bin/bash
set -e

# Argos Native Deployment Script
# This script prepares the application for production use via systemd.

echo "🚀 Starting Argos Deployment..."

# 1. Environment Validation
if [ ! -f ".env" ] && [ ! -f "/etc/argos/argos.env" ]; then
    echo "⚠️  No environment file found. Creating /etc/argos/argos.env from template..."
    sudo mkdir -p /etc/argos
    sudo cp .env.example /etc/argos/argos.env
    echo "Please edit /etc/argos/argos.env with production secrets before starting services."
fi

# 2. Dependency Management
echo "📦 Installing backend dependencies..."
cd backend && poetry install --only main && cd ..

echo "📦 Installing frontend dependencies..."
cd frontend && pnpm install && cd ..

# 3. Build Frontend
echo "🏗️  Building frontend assets..."
cd frontend && pnpm build && cd ..

# 4. Systemd Setup
echo "⚙️  Configuring systemd services..."
# Create a dedicated system user if it doesn't exist
if ! id "argos" &>/dev/null; then
    sudo useradd -r -s /bin/false argos || true
fi

# Template substitution and installation
# We assume the app is in /opt/argos for production paths in unit files
# Or we use current directory for a 'portable' style setup
INSTALL_DIR=$(pwd)

for template in ops/systemd/*.template; do
    service_name=$(basename "$template" .template)
    echo "Installing $service_name..."
    sed "s|/opt/argos|$INSTALL_DIR|g" "$template" > "/tmp/$service_name"
    sudo mv "/tmp/$service_name" "/etc/systemd/system/"
done

# 5. Finalize
echo "🔄 Reloading systemd and restarting services..."
sudo systemctl daemon-reload
sudo systemctl enable argos-backend argos-worker argos-frontend || true

echo "✅ Deployment complete!"
echo "-------------------------------------------------------"
echo "To start the application, run:"
echo "  sudo systemctl restart argos-backend argos-worker argos-frontend"
echo ""
echo "Monitor logs with:"
echo "  journalctl -u argos-backend -f"
echo "-------------------------------------------------------"
