# Traditional shell.nix for non-flake Nix users
# This provides a development shell without requiring flakes
# 
# Usage: nix-shell

let
  # Use builtin fetchTarball which should work even with daemon issues
  # Let Nix calculate the hash on first run
  nixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz";
  }) {};

  pkgs = nixpkgs;

  # Python 3.11 with Poetry
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    pkgs.poetry
  ]);

  # Playwright system dependencies
  playwrightDeps = with pkgs; [
    alsa-lib
    nss
    nspr
    atk
    at-spi2-atk
    cups
    dbus
    expat
    fontconfig
    freetype
    gdk-pixbuf
    glib
    gtk3
    libdrm
    libxkbcommon
    mesa
    pango
    xorg.libX11
    xorg.libXcomposite
    xorg.libXdamage
    xorg.libXext
    xorg.libXfixes
    xorg.libXi
    xorg.libXrandr
    xorg.libXrender
    xorg.libXScrnSaver
    xorg.libXtst
    xorg.libxcb
    xorg.libxshmfence
  ];

in
pkgs.mkShell {
  buildInputs = with pkgs; [
    # Development tools
    git
    curl
    jq
    docker
    docker-compose
    
    # Python
    python311
    pythonEnv
    poetry
    
    # Node.js
    nodejs_20
    nodePackages.pnpm
    nodePackages.typescript
    nodePackages.playwright
    
    # Playwright dependencies
  ] ++ playwrightDeps;

  shellHook = ''
    echo "Cortex Development Environment (Traditional Nix)"
    echo "================================================"
    echo "Python: $(python --version)"
    echo "Node.js: $(node --version)"
    echo "pnpm: $(pnpm --version)"
    echo "Poetry: $(poetry --version)"
    echo ""
    echo "Available commands:"
    echo "  - Backend: cd backend && poetry install && poetry run uvicorn app.main:app --reload"
    echo "  - Frontend: cd frontend && pnpm install && pnpm dev"
    echo "  - E2E Tests: pnpm e2e"
    echo "  - Docker services: docker-compose -f ops/docker-compose.yml up -d"
    echo ""
    
    # Set environment variables
    export CORTEX_ENV=dev
    export CORTEX_QDRANT_URL="http://localhost:6333"
    export CORTEX_DB_URL="postgresql+psycopg://cortex:cortex@localhost:5432/cortex"
    export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright"
    
    # Install Playwright browsers if not already installed
    if [ ! -d "$HOME/.cache/ms-playwright" ]; then
      echo "Installing Playwright browsers..."
      pnpm exec playwright install --with-deps || true
    fi
    
    # Ensure Docker socket is accessible
    if [ -S /var/run/docker.sock ]; then
      export DOCKER_HOST=unix:///var/run/docker.sock
    fi
  '';

  # LD_LIBRARY_PATH for Playwright browsers
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath playwrightDeps;
}
