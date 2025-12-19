#!/bin/bash
set -e

# Argos Installation Script
# Supports Docker Compose and Systemd deployment modes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/argos"
CONFIG_DIR="/etc/argos"
SERVICE_USER="argos"
SERVICE_GROUP="argos"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}Error: This script should not be run as root. Use sudo if needed.${NC}"
    exit 1
fi

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to check system requirements
check_requirements() {
    local mode=$1

    print_info "Checking system requirements for $mode mode..."

    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        print_error "Unsupported operating system"
        exit 1
    fi

    source /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" && "$ID" != "centos" && "$ID" != "rhel" && "$ID" != "fedora" ]]; then
        print_warning "Untested OS: $PRETTY_NAME. Proceeding anyway..."
    fi

    # Check for required commands
    local required_commands=("curl" "git")
    if [[ "$mode" == "compose" ]]; then
        required_commands+=("docker" "docker-compose")
    elif [[ "$mode" == "systemd" ]]; then
        required_commands+=("systemctl" "useradd" "usermod")
    fi

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_error "Required command '$cmd' not found"
            if [[ "$cmd" == "docker" ]]; then
                echo "Install Docker: https://docs.docker.com/get-docker/"
            elif [[ "$cmd" == "docker-compose" ]]; then
                echo "Install Docker Compose: https://docs.docker.com/compose/install/"
            fi
            exit 1
        fi
    done

    print_success "System requirements check passed"
}

# Function to install Docker Compose mode
install_compose() {
    print_info "Installing Argos with Docker Compose..."

    # Create directories
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$CONFIG_DIR"

    # Clone/update repository
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        print_info "Updating existing Argos installation..."
        cd "$INSTALL_DIR"
        git pull
    else
        print_info "Cloning Argos repository..."
        sudo git clone https://github.com/your-org/argos.git "$INSTALL_DIR"
        sudo chown -R "$USER:$USER" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    # Copy environment template
    if [[ ! -f "$CONFIG_DIR/.env" ]]; then
        cp "ops/.env.example.prod" "$CONFIG_DIR/.env"
        print_warning "Environment file created at $CONFIG_DIR/.env"
        print_warning "Please edit this file with your secrets before starting services"
    fi

    # Create Docker network
    docker network create argos-backend 2>/dev/null || true
    docker network create argos-frontend 2>/dev/null || true

    print_success "Docker Compose installation completed"
    echo ""
    echo "Next steps:"
    echo "1. Edit $CONFIG_DIR/.env with your secrets"
    echo "2. Start services: cd $INSTALL_DIR && docker-compose -f ops/docker-compose.prod.yml up -d"
    echo "3. Check status: docker-compose -f ops/docker-compose.prod.yml ps"
}

# Function to install Systemd mode
install_systemd() {
    print_info "Installing Argos with Systemd..."

    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd not available. Use Docker Compose mode instead."
        exit 1
    fi

    # Create service user
    if ! id "$SERVICE_USER" &>/dev/null; then
        print_info "Creating service user '$SERVICE_USER'..."
        sudo useradd --system --shell /bin/bash --home-dir "/home/$SERVICE_USER" --create-home "$SERVICE_USER"
    fi

    # Create directories
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$CONFIG_DIR"
    sudo chown "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"

    # Clone/update repository
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        print_info "Updating existing Argos installation..."
        sudo -u "$SERVICE_USER" git -C "$INSTALL_DIR" pull
    else
        print_info "Cloning Argos repository..."
        sudo -u "$SERVICE_USER" git clone https://github.com/your-org/argos.git "$INSTALL_DIR"
    fi

    # Install Python dependencies
    print_info "Installing Python dependencies..."
    cd "$INSTALL_DIR/backend"
    sudo -u "$SERVICE_USER" bash -c "
        export PATH=/home/$SERVICE_USER/.local/bin:\$PATH
        curl -sSL https://install.python-poetry.org | python3 -
        /home/$SERVICE_USER/.local/bin/poetry install --no-dev
    "

    # Install Node.js dependencies
    print_info "Installing Node.js dependencies..."
    cd "$INSTALL_DIR/frontend"
    sudo -u "$SERVICE_USER" bash -c "
        npm install -g pnpm
        pnpm install --frozen-lockfile
        pnpm build
    "

    # Setup PostgreSQL
    print_info "Setting up PostgreSQL..."
    if command -v psql &> /dev/null; then
        # Create database and user
        sudo -u postgres createuser --createdb --no-superuser --no-createrole "$SERVICE_USER" 2>/dev/null || true
        sudo -u postgres createdb --owner="$SERVICE_USER" cortex 2>/dev/null || true
    else
        print_warning "PostgreSQL not found. Please install and configure it manually."
    fi

    # Create environment file
    if [[ ! -f "$CONFIG_DIR/argos.env" ]]; then
        cat > "$CONFIG_DIR/argos.env" << EOF
# Argos Environment Configuration
ARGOS_ENV=strix
ARGOS_AUTH_SECRET=$(openssl rand -hex 32)
ARGOS_DATABASE_URL=postgresql://$SERVICE_USER@localhost:5432/cortex
ARGOS_QDRANT_URL=http://localhost:6333
ARGOS_REDIS_URL=redis://localhost:6379/0
CORTEX_ALLOW_NON_NIX=1

# Add other required variables here
# ARGOS_LANE_SUPER_READER_URL=...
EOF
        sudo chown root:root "$CONFIG_DIR/argos.env"
        sudo chmod 600 "$CONFIG_DIR/argos.env"
        print_warning "Environment file created at $CONFIG_DIR/argos.env"
        print_warning "Please review and update configuration as needed"
    fi

    # Install systemd services
    print_info "Installing systemd services..."

    # Backend service
    sed "s|/opt/argos|$INSTALL_DIR|g" "ops/systemd/argos-backend.service.template" | \
        sudo tee "/etc/systemd/system/argos-backend.service" > /dev/null

    # Worker service
    sed "s|/opt/argos|$INSTALL_DIR|g" "ops/systemd/argos-worker.service.template" | \
        sudo tee "/etc/systemd/system/argos-worker.service" > /dev/null

    # Frontend service
    sed "s|/opt/argos|$INSTALL_DIR|g" "ops/systemd/argos-frontend.service.template" | \
        sudo tee "/etc/systemd/system/argos-frontend.service" > /dev/null

    # Reload systemd
    sudo systemctl daemon-reload

    print_success "Systemd installation completed"
    echo ""
    echo "Next steps:"
    echo "1. Review $CONFIG_DIR/argos.env configuration"
    echo "2. Start services:"
    echo "   sudo systemctl start argos-backend argos-worker argos-frontend"
    echo "3. Enable auto-start:"
    echo "   sudo systemctl enable argos-backend argos-worker argos-frontend"
    echo "4. Check status:"
    echo "   sudo systemctl status argos-backend"
}

# Main menu
show_menu() {
    echo "========================================"
    echo "       Argos Installation Script"
    echo "========================================"
    echo ""
    echo "Choose deployment mode:"
    echo "1) Docker Compose (Recommended)"
    echo "2) Systemd (Bare metal)"
    echo "3) Exit"
    echo ""
    read -p "Enter choice [1-3]: " choice

    case $choice in
        1)
            check_requirements "compose"
            install_compose
            ;;
        2)
            check_requirements "systemd"
            install_systemd
            ;;
        3)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter 1, 2, or 3."
            show_menu
            ;;
    esac
}

# Run main menu
show_menu