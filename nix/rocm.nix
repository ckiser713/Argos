# nix/rocm.nix
{ pkgs }:

pkgs.mkShell {
  name = "rocm-shell";
  
  # This is a basic shell. You may need to add more packages 
  # from the rocm overlay depending on your needs.
  buildInputs = with pkgs; [
    rocm-smi
  ];

  shellHook = ''
    echo "Entered ROCm shell"
    echo "rocm-smi is available on the path"
  '';
}
