#!/usr/bin/env bash
set -euo pipefail

# Install Playwright host dependencies on Ubuntu/Debian
# This script requires sudo privileges
# Requirements:
#  - System `python3` should point to Python 3.11 on Ubuntu/Debian hosts to avoid dpkg python post-install failures.
#    If not, consider running: `sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1` (user must understand the implications)

if [[ $(id -u) -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "Detected apt-get, installing packages..."
  # Check that system python3 is 3.11 to avoid dpkg post-install script failures
  if command -v python3 >/dev/null 2>&1; then
    SYS_PY_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || true)
    if [[ -n "$SYS_PY_VER" && ! "$SYS_PY_VER" =~ ^3\.11 ]]; then
      echo "⚠ System 'python3' is version $SYS_PY_VER. Installing python3-apt and other packages may fail if system Python differs from 3.11."
      echo "⚠ This commonly happens on systems where 'python3' points to 3.12 or other versions."
      echo "⚠ Consider using one of the following options:"
      echo "  - Install Python 3.11 and make it the system default (sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1)"
      echo "  - Manually install host deps without 'python3-apt' (see playwright docs)."
      echo "⚠ Skipping automatic host dependency install to avoid dpkg failures."
      exit 1
    fi
  fi
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
