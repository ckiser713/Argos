{
  description = "A comprehensive development environment for Argos_Chatgpt (Project Argos)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
      let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      rocmPackages = pkgs.rocmPackages;
      
      # Avoid packaging large directories (model artifacts, caches) into the flake source
      # when building the development shell. This prevents 'argument list too long' errors
      # when Nix builds derivations based on the repository contents.
      filteredSource = builtins.filterSource (path: type: 
        (builtins.match "^(ops/models|node_modules|\\.venv|\\.cache|rocm|ops/models/.*)$" path) == null
      ) ./.;
      projectRoot = builtins.toString filteredSource;
      
      # Import vLLM module
      vllmModule = import ./nix/vllm.nix { inherit pkgs rocmPackages; lib = pkgs.lib; };
      
      # Backend package - wrapper script that uses poetry
      backend = pkgs.symlinkJoin {
        name = "argos-backend";
        paths = [ backend-runner ];
        buildInputs = [ pkgs.python311 pkgs.poetry ];
      };
      
      # Frontend package - wrapper script that uses pnpm
      frontend = pkgs.symlinkJoin {
        name = "argos-frontend";
        paths = [ frontend-runner ];
        buildInputs = [ pkgs.nodejs_20 pkgs.nodePackages.pnpm ];
      };
      
      # Service runner scripts
      backend-runner = pkgs.writeShellScriptBin "argos-backend-run" ''
        set -e
        cd ${projectRoot}/backend
        export ARGOS_ENV=production
        export ARGOS_QDRANT_URL=http://localhost:6333
        export ARGOS_ATLAS_DB_PATH=${projectRoot}/backend/atlas.db
        ${pkgs.poetry}/bin/poetry run ${pkgs.python311}/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
      '';
      
      frontend-runner = pkgs.writeShellScriptBin "argos-frontend-run" ''
        set -e
        cd ${projectRoot}/frontend
        export NODE_ENV=development
        ${pkgs.nodePackages.pnpm}/bin/pnpm dev
      '';
      
      docker-services-runner = pkgs.writeShellScriptBin "argos-docker-run" ''
        set -e
        cd ${projectRoot}
        ${pkgs.docker-compose}/bin/docker-compose -f ${projectRoot}/ops/docker-compose.yml up -d
      '';
      
      docker-services-stopper = pkgs.writeShellScriptBin "argos-docker-stop" ''
        set -e
        cd ${projectRoot}
        ${pkgs.docker-compose}/bin/docker-compose -f ${projectRoot}/ops/docker-compose.yml down
      '';
      
    in
    {
      # Development shell
      devShells.x86_64-linux.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          # ============================================
          # Python Environment
          # ============================================
          python311
          python311Packages.pip
          python311Packages.setuptools
          poetry

          # ============================================
          # Node.js Environment
          # ============================================
          nodejs_20  # Node.js 20+ as specified in docs (fallback to nodejs if not available)
          nodePackages.pnpm
          nodePackages.typescript
          nodePackages.typescript-language-server

          # ============================================
          # Python Linters & Type Checkers
          # ============================================
          ruff
          mypy
          python311Packages.black  # Optional but useful

          # ============================================
          # vLLM and ROCm Tools (optional)
          # ============================================
          vllmModule.vllmServer
          vllmModule.vllmHealthCheck
          rocmPackages.rocm-smi

          # ============================================
          # System Libraries for Python Packages
          # ============================================
          # Core C libraries
          stdenv.cc.cc.lib
          gcc
          gnumake
          binutils
          
          # libffi - Required for bcrypt (passlib dependency)
          libffi
          
          # OpenSSL - Required for HTTPS/SSL connections (FastAPI, uvicorn, requests)
          openssl
          openssl.dev
          
          # Compression libraries - Required by various Python packages
          zlib
          zlib.dev
          bzip2
          xz
          
          # SQLite - Headers needed for Python sqlite3 module (though built-in)
          sqlite
          sqlite.dev
          
          # tree-sitter - Required for tree-sitter-languages Python package
          tree-sitter
          
          # Additional libraries that may be needed
          libxml2
          libxslt
          expat
          ncurses
          readline
          
          # ============================================
          # Database Tools
          # ============================================
          postgresql_16
          postgresql16Packages.pgvector

          # ============================================
          # Docker & Container Tools
          # ============================================
          docker
          docker-compose
          
          # ============================================
          # Playwright Browsers & Dependencies
          # ============================================
          chromium
          firefox
          webkitgtk_6_0
          
          # Playwright system dependencies
          # These are typically provided by the browsers, but we include
          # common system libraries that might be needed
          glib
          nss
          nspr
          alsa-lib
          atk
          at-spi2-atk
          libdrm
          libxkbcommon
          xorg.libXcomposite
          xorg.libXdamage
          xorg.libX11
          xorg.libXext
          xorg.libXfixes
          xorg.libXrandr
          xorg.libXcursor  # Required for Playwright (libxcursor.so.1)
          xorg.libXi  # Required for Playwright (libXi.so.6)
          xorg.libXrender  # Required for Playwright (libXrender.so.1)
          # note: libXss is not available as xorg.libXss in this nixpkgs;
          # other X.org libs are included above (libX11, libXext, libXrender)
          libx11
          libxext
          libxcb
          mesa
          libgbm
          udev
          cups  # Required for Playwright (libcups.so.2)
          pango
          cairo
          gdk-pixbuf
          gtk3
          dbus
          fontconfig
          freetype
          # Common fonts used in the app for visual consistency
          noto-fonts
          noto-fonts-color-emoji
          liberation_ttf
          dejavu_fonts
          # Additional packages to satisfy Playwright host dependency checks
          harfbuzz
          icu
          vulkan-loader
          # GStreamer and its plugins used by browsers
          gst_all_1.gstreamer
          gst_all_1.gst-plugins-base
          gst_all_1.gst-plugins-good
          gst_all_1.gst-plugins-bad
          gst_all_1.gst-plugins-ugly
          gst_all_1.gst-libav
          # Common multimedia and encoding libraries
          libvpx
          libavif
          woff2
          libwebp
          libjpeg_turbo
          libpng
          # Crypto and helper libs
          libgcrypt
          libgpg-error
          # Wayland/graphics support
          wayland
          wayland-protocols
          # GTK4 and related graphic libraries requested by Playwright
          gtk4
          graphene
          lcms2
          flite
          libsecret
          
          # ============================================
          # Development Tools
          # ============================================
          git
          curl
          wget
          jq  # Useful for JSON processing
          bash
          # Rust toolchain (may be required to build certain Python wheels like tree-sitter-languages)
          rustc
          cargo
          pkg-config  # For finding library paths during Python package builds
          
          # ============================================
          # ROCm Support (for AMD GPU)
          # ============================================
          # ROCm wheels and binaries are provided from /home/nexus/amd-ai/artifacts/
          # This includes:
          #   - PyTorch 2.9.1 (ROCm-enabled) wheel in vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl
          #   - vLLM 0.12.0 wheel in vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl
          #   - llama.cpp binaries (llama-cli, llama-server, llama-quantize) in bin/
          # These are configured via PIP_FIND_LINKS and PATH environment variables
          # rocmPackages.rocm-smi  # Optional: uncomment if you need rocm-smi tool
        ];

        # ============================================
        # Environment Variables
        # ============================================
        shellHook = ''
          # Add ROCm binaries to PATH (llama-cli, llama-server, llama-quantize)
          export PATH="/home/nexus/amd-ai/artifacts/bin:$PATH"
          # Ensure the Python from Nix (Python 3.11) is first in PATH so Poetry uses it
          export PATH="${pkgs.python311}/bin:${pkgs.poetry}/bin:$PATH"
          # Prefer active Python for Poetry virtualenvs so it uses Python 3.11
          export POETRY_VIRTUALENVS_CREATE=true
          # Create venv in-project for reproducible per-project environments
          export POETRY_VIRTUALENVS_IN_PROJECT=true
          
          echo "=========================================="
          echo "Argos Development Environment"
          echo "=========================================="
          echo ""
          # Prefer Python 3.11 where available
          echo "Python: $(python3.11 --version 2>/dev/null || python3 --version 2>/dev/null)"
          echo "Node.js: $(node --version)"
          echo "pnpm: $(pnpm --version)"
          echo "Poetry: $(poetry --version)"
          echo ""
          echo "ROCm Integration:"
          echo "  - ROCm wheels: /home/nexus/amd-ai/artifacts/vllm_docker_rocm/"
          echo "  - ROCm binaries: /home/nexus/amd-ai/artifacts/bin (added to PATH)"
          echo "  - PIP_FIND_LINKS configured for offline PyTorch installation"
          echo ""
          echo "Environment variables set:"
          echo "  - ARGOS_ENV=local (can be overridden by setting ARGOS_ENV before 'nix develop')"
          echo "  - ARGOS_QDRANT_URL=http://localhost:6333"
          echo "  - PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright"
          echo "  - PIP_FIND_LINKS=/home/nexus/amd-ai/artifacts/vllm_docker_rocm"
          echo "  - PIP_NO_INDEX not set (allows Poetry/pip to access PyPI)"
          echo "  - For ROCm packages, use: pip install --no-index --find-links /home/nexus/amd-ai/artifacts/vllm_docker_rocm/ ..."
          echo ""
          echo "To install PyTorch and vLLM from ROCm wheels:"
          echo "  pip install --find-links /home/nexus/amd-ai/artifacts/vllm_docker_rocm/ torch vllm"
          echo ""
          echo "ROCm binaries available:"
          if [ -f "/home/nexus/amd-ai/artifacts/bin/llama-cli" ]; then
            echo "  ✓ llama-cli (ROCm-optimized)"
          else
            echo "  ⚠ llama-cli not found at /home/nexus/amd-ai/artifacts/bin/llama-cli"
          fi
          if [ -f "/home/nexus/amd-ai/artifacts/bin/llama-server" ]; then
            echo "  ✓ llama-server (ROCm-optimized)"
          else
            echo "  ⚠ llama-server not found at /home/nexus/amd-ai/artifacts/bin/llama-server"
          fi
          echo ""
          echo "PostgreSQL 16:"
          echo "  - PostgreSQL: $(psql --version 2>/dev/null | head -1 || echo 'Not available')"
          echo "  - pgvector: Available via CREATE EXTENSION pgvector;"
          echo ""
          # Rebuild the font cache so Playwright uses the fonts installed in Nix
          if command -v fc-cache >/dev/null 2>&1; then
            fc-cache -f -v || true
          fi
          echo "=========================================="
        '';

        # Set environment variables for the development environment
        # Note: ARGOS_ENV is NOT set here to allow external override
        # Defaults to "local" via Settings class if not set externally
        # For staging: ARGOS_ENV=strix nix develop --command ...
        # For production: ARGOS_ENV=production nix develop --command ...
        ARGOS_QDRANT_URL = "http://localhost:6333";
        ARGOS_DATABASE_URL = "postgresql://argos:argos@localhost:5432/argos";
        PLAYWRIGHT_BROWSERS_PATH = "$HOME/.cache/ms-playwright";
        
        # ROCm Integration - Python 3.11 PyTorch 2.9 and vLLM 0.12.0 wheels
        # Point pip to ROCm wheels for offline installation
        # Wheels available:
        #   - vllm_docker_rocm/: torch-2.9.1-cp311-cp311-linux_x86_64.whl, vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl
        # Note: PIP_NO_INDEX is NOT set globally to allow Poetry/pip to access PyPI for other packages
        # When installing ROCm packages, use: pip install --no-index --find-links /home/nexus/amd-ai/artifacts/vllm_docker_rocm/ ...
        PIP_FIND_LINKS = "/home/nexus/amd-ai/artifacts/vllm_docker_rocm";
        
        # ROCm binaries (llama.cpp tools) are added to PATH in shellHook
        # These are: llama-cli, llama-server, llama-quantize
        # Located at: /home/nexus/amd-ai/artifacts/bin
        
        # Python environment setup
        PYTHONPATH = "${pkgs.python311}/lib/python3.11/site-packages";
        
        # Library paths for Python packages that need native libraries
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
          stdenv.cc.cc.lib
          libffi
          openssl
          zlib
          sqlite
          tree-sitter
          libxml2
          libxslt
          expat
          ncurses
          readline
          # Playwright/browser dependencies
          glib
          nss
          nspr
          alsa-lib
          atk
          at-spi2-atk
          libdrm
          libxkbcommon
          xorg.libXcomposite
          xorg.libXdamage
          xorg.libX11
          xorg.libXext
          xorg.libXfixes
          xorg.libXrandr
          xorg.libXcursor
          xorg.libXi
          xorg.libXrender
          libxcb
          mesa
          libgbm
          udev
          cups
          pango
          cairo
          gdk-pixbuf
          gtk3
          dbus
          fontconfig
          freetype
        ]);
        
        # Ensure pkg-config can find libraries
        PKG_CONFIG_PATH = pkgs.lib.makeSearchPath "lib/pkgconfig" (with pkgs; [
          libffi
          openssl
          zlib
          sqlite
          libxml2
          libxslt
        ]);
        
        # C compiler flags
        CFLAGS = "-I${pkgs.libffi.dev}/include -I${pkgs.openssl.dev}/include -I${pkgs.zlib.dev}/include -I${pkgs.sqlite.dev}/include";
        LDFLAGS = "-L${pkgs.libffi}/lib -L${pkgs.openssl}/lib -L${pkgs.zlib}/lib -L${pkgs.sqlite}/lib";
      };
      
      # Packages
      packages.x86_64-linux = {
        backend = backend;
        frontend = frontend;
        default = backend; # Default package
      };
      
      # Apps for running services
      apps.x86_64-linux = {
        backend = {
          type = "app";
          program = "${backend-runner}/bin/argos-backend-run";
        };
        frontend = {
          type = "app";
          program = "${frontend-runner}/bin/argos-frontend-run";
        };
        docker-up = {
          type = "app";
          program = "${docker-services-runner}/bin/argos-docker-run";
        };
        docker-down = {
          type = "app";
          program = "${docker-services-stopper}/bin/argos-docker-stop";
        };
        default = {
          type = "app";
          program = "${backend-runner}/bin/argos-backend-run";
        };
      };
      
      # NixOS module for systemd services
      nixosModules.default = import ./nix/services.nix;
      
      # ============================================================
      # vLLM Packages and Shells
      # ============================================================
      
      packages.x86_64-linux = {
        # vLLM server executable
        vllm-server = vllmModule.vllmServer;
        
        # Health check utility
        vllm-health = vllmModule.vllmHealthCheck;
        
        # OCI container image
        vllm-container = vllmModule.vllmOciImage;
        
        # Complete vLLM toolset
        vllm-tools = vllmModule.vllmComplete;
      };
      
      # Development shells
      devShells.x86_64-linux = {
        # vLLM development/runtime shell
        vllm = vllmModule.vllmRuntimeShell;
        
        # vLLM with additional debugging tools
        vllm-debug = pkgs.mkShell {
          inputsFrom = [ vllmModule.vllmRuntimeShell ];
          buildInputs = with pkgs; [
            gdb
            linuxPackages.perf
            valgrind
            strace
          ];
        };
      };
    };
}
