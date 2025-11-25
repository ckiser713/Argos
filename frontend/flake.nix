{
  description = "Cortex Frontend - React TypeScript Application";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        nodejs = pkgs.nodejs_20;
        pnpm = pkgs.nodePackages.pnpm;

        # Build the frontend package
        frontendPackage = pkgs.buildNpmPackage {
          pname = "cortex-frontend";
          version = "0.1.0";
          src = ./.;

          npmDepsHash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="; # Will be updated after first build

          nativeBuildInputs = [
            nodejs
            pnpm
            pkgs.makeWrapper
          ];

          # Use pnpm instead of npm
          npmBuildFlags = [ "--" "--package-manager=pnpm" ];

          buildPhase = ''
            runHook preBuild
            
            # Install dependencies with pnpm
            export HOME=$TMPDIR
            pnpm install --frozen-lockfile --no-optional
            
            # Build the application
            pnpm run build
            
            runHook postBuild
          '';

          installPhase = ''
            runHook preInstall
            
            # Copy built files
            mkdir -p $out
            cp -r dist $out/
            
            # Copy package.json for reference
            cp package.json $out/
            
            # Create a wrapper script to run the dev server
            mkdir -p $out/bin
            cat > $out/bin/cortex-frontend-dev <<EOF
            #!${pkgs.bash}/bin/bash
            cd $out
            exec ${nodejs}/bin/node ${pnpm}/lib/node_modules/pnpm/bin/pnpm.cjs dev "\$@"
            EOF
            chmod +x $out/bin/cortex-frontend-dev
            
            runHook postInstall
          '';

          # Don't run tests during build
          doCheck = false;
        };

        # Development shell
        devShell = pkgs.mkShell {
          buildInputs = [
            nodejs
            pnpm
            pkgs.nodePackages.typescript
            pkgs.nodePackages.vite
          ];

          shellHook = ''
            echo "Cortex Frontend Development Shell"
            echo "=================================="
            echo "Node.js: $(node --version)"
            echo "pnpm: $(pnpm --version)"
            echo ""
            echo "To install dependencies:"
            echo "  pnpm install"
            echo ""
            echo "To run the dev server:"
            echo "  pnpm dev"
            echo ""
            echo "To build:"
            echo "  pnpm build"
            echo ""
          '';
        };

      in
      {
        packages.default = frontendPackage;

        devShells.default = devShell;
      }
    );
}

