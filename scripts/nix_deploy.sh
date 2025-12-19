#!/usr/bin/env bash
set -e

# scripts/nix_deploy.sh
# ------------------------------------------------------------------
# Deploys Argos using the Nix environment to ensure 100% reproducibility.
# Generates systemd units that point to the immutable /nix/store paths
# for Python, Node, Poetry, and pnpm.
# ------------------------------------------------------------------

# 1. Ensure we are inside the Nix shell
if [ -z "$IN_NIX_SHELL" ]; then
    echo "🔄 Entering Nix environment..."
    # Re-execute this script inside 'nix develop'
    # We use --command to run this same script again
    exec nix develop --command "$0" "$@"
fi

echo "🚀 Starting Argos Nix Deployment..."

# 2. Resolve Nix Store Paths for Tools
# Since we are in the shell, 'which' gives us the store path.
POETRY_BIN=$(which poetry)
PNPM_BIN=$(which pnpm)
UVICORN_BIN=$(which uvicorn) # Will likely be inside the poetry venv, handling later
PYTHON_BIN=$(which python3)

echo "🔍 Resolved Tool Paths:"
echo "   Poetry: $POETRY_BIN"
echo "   pnpm:   $PNPM_BIN"
echo "   Python: $PYTHON_BIN"

# 3. Build & Install Dependencies (Reproducible)
echo "📦 Installing backend dependencies (via Nix Poetry)..."
cd backend
$POETRY_BIN install --only main
cd ..

echo "📦 Installing frontend dependencies (via Nix pnpm)..."
cd frontend
$PNPM_BIN install
echo "🏗️  Building frontend assets..."
$PNPM_BIN build
cd ..

# 4. Generate Systemd Units with Nix Paths
# We assume the app is running from the current directory (Production source)
INSTALL_DIR=$(pwd)
SYSTEMD_DIR="ops/systemd"

echo "⚙️  Generating Nix-linked Systemd Services..."

# --- Backend Service ---
cat <<EOF > $SYSTEMD_DIR/argos-backend.service.nix_generated
[Unit]
Description=Argos Backend (Nix)
After=network.target

[Service]
User=argos
Group=argos
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=/etc/argos/argos.env
# We use 'poetry run' from the Nix store path
ExecStart=$POETRY_BIN run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# --- Worker Service ---
cat <<EOF > $SYSTEMD_DIR/argos-worker.service.nix_generated
[Unit]
Description=Argos Worker (Nix)
After=network.target

[Service]
User=argos
Group=argos
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=/etc/argos/argos.env
ExecStart=$POETRY_BIN run celery -A app.worker worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# --- Frontend Service ---
cat <<EOF > $SYSTEMD_DIR/argos-frontend.service.nix_generated
[Unit]
Description=Argos Frontend (Nix)
After=network.target argos-backend.service

[Service]
User=argos
Group=argos
WorkingDirectory=$INSTALL_DIR/frontend
EnvironmentFile=/etc/argos/argos.env
# Use Nix pnpm to serve
ExecStart=$PNPM_BIN run preview --host 0.0.0.0 --port 5173
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Installation (Requires Sudo)
echo "💾 Installing services to /etc/systemd/system/..."

# Create user if needed
if ! id "argos" &>/dev/null; then
    echo "   Creating 'argos' system user..."
    sudo useradd -r -s /bin/false argos || true
fi

# Ensure env file exists
if [ ! -f "/etc/argos/argos.env" ]; then
    echo "   Creating /etc/argos/argos.env..."
    sudo mkdir -p /etc/argos
    sudo cp .env.example /etc/argos/argos.env
fi

sudo mv $SYSTEMD_DIR/*.nix_generated /etc/systemd/system/
# Rename them to remove the .nix_generated suffix during move? No, simpler to copy to correct names.
sudo mv /etc/systemd/system/argos-backend.service.nix_generated /etc/systemd/system/argos-backend.service
sudo mv /etc/systemd/system/argos-worker.service.nix_generated /etc/systemd/system/argos-worker.service
sudo mv /etc/systemd/system/argos-frontend.service.nix_generated /etc/systemd/system/argos-frontend.service

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable argos-backend argos-worker argos-frontend || true

echo "✅ Nix Deployment Complete!"
echo "   Binaries are linked to: /nix/store/..."
echo "   Run 'sudo systemctl restart argos-backend argos-worker argos-frontend' to start."
