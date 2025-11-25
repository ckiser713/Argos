{
  description = "Cortex - AI-Integrated Knowledge & Execution Engine";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ poetry2nix.overlays.default ];
        };

        # Python 3.11
        pythonEnv = pkgs.python311;

        # Node.js 20 with pnpm
        nodejs = pkgs.nodejs_20;
        pnpm = pkgs.nodePackages.pnpm;

        # Playwright system dependencies
        playwrightDeps = with pkgs; [
          # Audio support
          alsa-lib
          # Browser dependencies
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

        # Development tools
        devTools = with pkgs; [
          git
          curl
          jq
          docker
          docker-compose
          # Python tools
          python311
          pythonEnv
          poetry
          # Node.js tools
          nodejs
          pnpm
          # TypeScript
          nodePackages.typescript
        ];

        # Import sub-flakes
        backendFlake = import ./backend/flake.nix {
          inherit nixpkgs poetry2nix flake-utils;
        };

        frontendFlake = import ./frontend/flake.nix {
          inherit nixpkgs flake-utils;
        };

        # Docker compose wrapper script
        dockerComposeWrapper = pkgs.writeScriptBin "cortex-docker" ''
          #!${pkgs.bash}/bin/bash
          set -e
          # Find project root by looking for flake.nix or ops/docker-compose.yml
          PROJECT_ROOT="$PWD"
          while [ "$PROJECT_ROOT" != "/" ]; do
            if [ -f "$PROJECT_ROOT/flake.nix" ] || [ -f "$PROJECT_ROOT/ops/docker-compose.yml" ]; then
              break
            fi
            PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
          done
          if [ "$PROJECT_ROOT" = "/" ]; then
            echo "Error: Could not find project root (flake.nix or ops/docker-compose.yml)" >&2
            exit 1
          fi
          cd "$PROJECT_ROOT"
          exec ${pkgs.docker-compose}/bin/docker-compose -f ops/docker-compose.yml "$@"
        '';

      in
      {
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = devTools ++ playwrightDeps ++ [ dockerComposeWrapper ];

          shellHook = ''
            echo "Cortex Development Environment"
            echo "=============================="
            echo "Python: $(python --version)"
            echo "Node.js: $(node --version)"
            echo "pnpm: $(pnpm --version)"
            echo ""
            echo "Available commands:"
            echo "  - Backend: cd backend && poetry install && poetry run uvicorn app.main:app --reload"
            echo "  - Frontend: cd frontend && pnpm install && pnpm dev"
            echo "  - E2E Tests: pnpm e2e"
            echo "  - Docker services: cortex-docker up -d"
            echo "  - Docker services (stop): cortex-docker down"
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
        };

        # Build outputs
        packages = {
          backend = backendFlake.packages.${system}.default;
          frontend = frontendFlake.packages.${system}.default;
          docker-compose = dockerComposeWrapper;

          default = pkgs.symlinkJoin {
            name = "cortex-full";
            paths = [
              self.packages.${system}.backend
              self.packages.${system}.frontend
            ];
          };
        };

        # Formatter
        formatter = pkgs.nixpkgs-fmt;
      }
    );
}

