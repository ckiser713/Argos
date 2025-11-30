{
  description = "A comprehensive development environment for Argos_Chatgpt (Project Cortex)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
      let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      # Avoid packaging large directories (model artifacts, caches) into the flake source
      # when building the development shell. This prevents 'argument list too long' errors
      # when Nix builds derivations based on the repository contents.
      filteredSource = builtins.filterSource (path: type: 
        (builtins.match "^(ops/models|node_modules|\\.venv|\\.cache|rocm|ops/models/.*)$" path) == null
      ) ./.;
      projectRoot = builtins.toString filteredSource;
      
      # Backend package - wrapper script that uses poetry
      backend = pkgs.symlinkJoin {
        name = "cortex-backend";
        paths = [ backend-runner ];
        buildInputs = [ pkgs.python311 pkgs.poetry ];
      };
      
      # Frontend package - wrapper script that uses pnpm
      frontend = pkgs.symlinkJoin {
        name = "cortex-frontend";
        paths = [ frontend-runner ];
        buildInputs = [ pkgs.nodejs_20 pkgs.nodePackages.pnpm ];
      };
      
      # Service runner scripts
      backend-runner = pkgs.writeShellScriptBin "cortex-backend-run" ''
        set -e
        cd ${projectRoot}/backend
        export CORTEX_ENV=production
        export CORTEX_QDRANT_URL=http://localhost:6333
        export CORTEX_ATLAS_DB_PATH=${projectRoot}/backend/atlas.db
        ${pkgs.poetry}/bin/poetry run ${pkgs.python311}/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
      '';
      
      frontend-runner = pkgs.writeShellScriptBin "cortex-frontend-run" ''
        set -e
        cd ${projectRoot}/frontend
        export NODE_ENV=development
        ${pkgs.nodePackages.pnpm}/bin/pnpm dev
      '';
      
      docker-services-runner = pkgs.writeShellScriptBin "cortex-docker-run" ''
        set -e
        cd ${projectRoot}
        ${pkgs.docker-compose}/bin/docker-compose -f ${projectRoot}/ops/docker-compose.yml up -d
      '';
      
      docker-services-stopper = pkgs.writeShellScriptBin "cortex-docker-stop" ''
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
          # ROCm wheels and binaries are provided from ~/rocm/py311-tor290/
          # This includes:
          #   - PyTorch 2.9.1 (ROCm-enabled) wheels in wheels/torch2.9/
          #   - Common dependencies (triton, tokenizers) in wheels/common/
          #   - llama.cpp binaries (llama-cpp, llama-bench, llama-quantize) in bin/
          #   - vLLM Docker image in images/
          # These are configured via PIP_FIND_LINKS and PATH environment variables
          # rocmPackages.rocm-smi  # Optional: uncomment if you need rocm-smi tool
        ];

        # ============================================
        # Environment Variables
        # ============================================
        shellHook = ''
          # Add ROCm binaries to PATH (llama-cpp, llama-bench, llama-quantize)
          export PATH="$HOME/rocm/py311-tor290/bin:$PATH"
          # Ensure the Python from Nix (Python 3.11) is first in PATH so Poetry uses it
          export PATH="${pkgs.python311}/bin:${pkgs.poetry}/bin:$PATH"
          # Prefer active Python for Poetry virtualenvs so it uses Python 3.11
          export POETRY_VIRTUALENVS_CREATE=true
          # Create venv in-project for reproducible per-project environments
          export POETRY_VIRTUALENVS_IN_PROJECT=true
          
          echo "=========================================="
          echo "Cortex Development Environment"
          echo "=========================================="
          echo ""
          # Prefer Python 3.11 where available
          echo "Python: $(python3.11 --version 2>/dev/null || python3 --version 2>/dev/null)"
          echo "Node.js: $(node --version)"
          echo "pnpm: $(pnpm --version)"
          echo "Poetry: $(poetry --version)"
          echo ""
          echo "ROCm Integration:"
          echo "  - ROCm wheels: $HOME/rocm/py311-tor290/wheels"
          echo "  - ROCm binaries: $HOME/rocm/py311-tor290/bin (added to PATH)"
          echo "  - PIP_FIND_LINKS configured for offline PyTorch installation"
          echo ""
          echo "Environment variables set:"
          echo "  - CORTEX_ENV=local (can be overridden by setting CORTEX_ENV before 'nix develop')"
          echo "  - CORTEX_QDRANT_URL=http://localhost:6333"
          echo "  - PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright"
          echo "  - PIP_FIND_LINKS=$HOME/rocm/py311-tor290/wheels/torch2.9:$HOME/rocm/py311-tor290/wheels/common"
          echo "  - PIP_NO_INDEX not set (allows Poetry/pip to access PyPI)"
          echo "  - For ROCm packages, use: pip install --no-index --find-links \$HOME/rocm/py311-tor290/wheels/..."
          echo ""
          echo "To install PyTorch from ROCm wheels:"
          echo "  pip install --find-links $HOME/rocm/py311-tor290/wheels/torch2.9 torch torchvision torchaudio"
          echo "  pip install --find-links $HOME/rocm/py311-tor290/wheels/common triton tokenizers"
          echo ""
          echo "ROCm binaries available:"
          if [ -f "$HOME/rocm/py311-tor290/bin/llama-cpp" ]; then
            echo "  ✓ llama-cpp (ROCm-optimized)"
          else
            echo "  ⚠ llama-cpp not found at $HOME/rocm/py311-tor290/bin/llama-cpp"
          fi
          echo ""
          # Rebuild the font cache so Playwright uses the fonts installed in Nix
          if command -v fc-cache >/dev/null 2>&1; then
            fc-cache -f -v || true
          fi
          echo "=========================================="
        '';

        # Set environment variables for the development environment
        # CORTEX_ENV defaults to "local" but can be overridden by environment variable
        # This allows staging/production deployments to set CORTEX_ENV=strix or CORTEX_ENV=production
        CORTEX_ENV = builtins.getEnv "CORTEX_ENV" or "local";
        CORTEX_QDRANT_URL = "http://localhost:6333";
        CORTEX_DB_URL = "postgresql+psycopg://cortex:cortex@localhost:5432/cortex";
        PLAYWRIGHT_BROWSERS_PATH = "$HOME/.cache/ms-playwright";
        
        # ROCm Integration - Python 3.11 PyTorch 2.9 wheels
        # Point pip to ROCm wheels for offline installation
        # Wheels available:
        #   - torch2.9/: torch-2.9.1, torchvision-0.25.0, torchaudio-2.9.1
        #   - common/: triton-3.5.0, tokenizers-0.22.2
        # Note: PIP_NO_INDEX is NOT set globally to allow Poetry/pip to access PyPI for other packages
        # When installing ROCm packages, use: pip install --no-index --find-links $HOME/rocm/py311-tor290/wheels/...
        PIP_FIND_LINKS = "$HOME/rocm/py311-tor290/wheels/torch2.9:$HOME/rocm/py311-tor290/wheels/common";
        
        # ROCm binaries (llama.cpp tools) are added to PATH in shellHook
        # These are: llama-cpp, llama-bench, llama-quantize
        # Located at: ~/rocm/py311-tor290/bin
        
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
          program = "${backend-runner}/bin/cortex-backend-run";
        };
        frontend = {
          type = "app";
          program = "${frontend-runner}/bin/cortex-frontend-run";
        };
        docker-up = {
          type = "app";
          program = "${docker-services-runner}/bin/cortex-docker-run";
        };
        docker-down = {
          type = "app";
          program = "${docker-services-stopper}/bin/cortex-docker-stop";
        };
        default = {
          type = "app";
          program = "${backend-runner}/bin/cortex-backend-run";
        };
      };
      
      # NixOS module for systemd services
      nixosModules.default = import ./nix/services.nix;
    };
}
