# Docker services integration for Cortex
# This file provides NixOS container definitions as an alternative to docker-compose
# For now, we use docker-compose wrapper, but this can be migrated to pure NixOS containers

{ pkgs, lib, ... }:

{
  # Example NixOS container configuration (commented out for now)
  # To use this, you need NixOS or systemd-nspawn support
  
  # containers.qdrant = {
  #   autoStart = true;
  #   privateNetwork = true;
  #   hostAddress = "10.233.1.1";
  #   localAddress = "10.233.1.2";
  #   config = { config, pkgs, ... }: {
  #     services.qdrant = {
  #       enable = true;
  #     };
  #   };
  # };
  
  # For now, we use docker-compose via the wrapper script
  # See flake.nix for the dockerComposeWrapper
}

