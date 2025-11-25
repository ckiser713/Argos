{
  description = "Cortex Backend - FastAPI Python Application";

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
        python = pkgs.python311;

        # Poetry environment
        poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          python = python;
          preferWheels = true;
          overrides = pkgs.poetry2nix.defaultPoetryOverrides.extend (self: super: {
            # Add any package overrides here if needed
            # Example:
            # sentence-transformers = super.sentence-transformers.overridePythonAttrs (old: {
            #   buildInputs = (old.buildInputs or []) ++ [ pkgs.rustPlatform.cargoSetupHook ];
            # });
          });
        };

        # Backend package
        backendPackage = pkgs.buildPythonPackage {
          pname = "cortex-backend";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = with pkgs; [
            poetry
            python.pkgs.setuptools
            python.pkgs.wheel
          ];

          propagatedBuildInputs = [
            poetryEnv
          ];

          # Install the package
          installPhase = ''
            mkdir -p $out/lib/${python.libPrefix}/site-packages
            cp -r app $out/lib/${python.libPrefix}/site-packages/
            
            # Create a wrapper script to run uvicorn
            mkdir -p $out/bin
            cat > $out/bin/cortex-backend <<EOF
            #!${pkgs.bash}/bin/bash
            exec ${poetryEnv}/bin/python -m uvicorn app.main:app "\$@"
            EOF
            chmod +x $out/bin/cortex-backend
          '';

          # No tests in build phase
          doCheck = false;
        };

      in
      {
        packages.default = backendPackage;

        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = [
            poetryEnv
            pkgs.poetry
            python
            pkgs.python311Packages.pip
            pkgs.python311Packages.setuptools
            pkgs.python311Packages.wheel
          ];

          shellHook = ''
            echo "Cortex Backend Development Shell"
            echo "================================="
            echo "Python: $(python --version)"
            echo "Poetry: $(poetry --version)"
            echo ""
            echo "To install dependencies:"
            echo "  poetry install"
            echo ""
            echo "To run the server:"
            echo "  poetry run uvicorn app.main:app --reload"
            echo ""
            
            # Set environment variables
            export CORTEX_ENV=dev
            export CORTEX_QDRANT_URL="http://localhost:6333"
            export CORTEX_ATLAS_DB_PATH="./atlas.db"
          '';
        };
      }
    );
}

