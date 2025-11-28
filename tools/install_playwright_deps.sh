#!/usr/bin/env bash
set -euo pipefail

# Install Playwright host dependencies on Ubuntu/Debian
# This script requires sudo privileges

if [[ $(id -u) -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "Detected apt-get, installing packages..."
  # Avoid running post-invoke scripts that may import apt_pkg which might be missing
  $SUDO apt-get -o APT::Update::Post-Invoke-Success="" update -y
  # Ensure python3-apt is installed (provides apt_pkg for post-invoke scripts)
  $SUDO apt-get -o APT::Update::Post-Invoke-Success="" install -y python3-apt || true
  $SUDO apt-get -o APT::Update::Post-Invoke-Success="" install -y \
    libnss3 \
    libatk1.0-0 \
    libxss1 \
    libasound2 \
    libxcomposite1 \
    libxrandr2 \
    libxkbcommon-x11-0 \
    libgtk-3-0 \
    libgbm1 \
    libdrm2 \
    libx11-xcb1 \
    python3-apt
  echo "Playwright host dependencies installed."
else
  echo "Unsupported package manager. Please install Playwright host dependencies manually per https://playwright.dev/docs/intro."
  exit 1
fi
