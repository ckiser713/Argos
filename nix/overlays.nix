# Custom Nix overlays for Cortex project
# This file can be used to override packages or add custom packages

final: prev: {
  # Example: Custom Python package override
  # python311Packages = prev.python311Packages.overrideScope' (pythonFinal: pythonPrev: {
  #   sentence-transformers = pythonPrev.sentence-transformers.overridePythonAttrs (old: {
  #     # Add custom build inputs if needed
  #     buildInputs = (old.buildInputs or []) ++ [ ];
  #   });
  # });

  # Example: ROCm support overlay (for AMD GPU)
  # Uncomment and configure if building on AMD hardware with ROCm
  # rocmPackages = prev.rocmPackages.overrideScope' (rocmFinal: rocmPrev: {
  #   # Custom ROCm configuration
  # });

  # Example: Node.js package override
  # nodePackages = prev.nodePackages.overrideScope' (nodeFinal: nodePrev: {
  #   # Custom Node.js package overrides
  # });
}

