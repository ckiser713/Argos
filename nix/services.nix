# nix/services.nix
# Service definitions for Cortex deployment

{ config, pkgs, lib, ... }:

let
  # Project root - adjust this path as needed
  projectRoot = "/home/nexus/Argos_Chatgpt";
in
{
  # Backend service
  systemd.services.cortex-backend = {
    description = "Cortex Backend API Service";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" "docker.service" ];
    requires = [ "docker.service" ];
    
    serviceConfig = {
      Type = "simple";
      Restart = "always";
      RestartSec = "10s";
      User = "nexus";
      Group = "nexus";
      WorkingDirectory = "${projectRoot}/backend";
      EnvironmentFile = "/etc/cortex/cortex.env";
      Environment = [
        "CORTEX_ENV=production"
        "PATH=${pkgs.python311}/bin:${pkgs.poetry}/bin:$PATH"
      ];
      ExecStart = "${pkgs.bash}/bin/bash -c 'cd ${projectRoot}/backend && ${pkgs.poetry}/bin/poetry run ${pkgs.python311}/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'";
      ExecReload = "${pkgs.coreutils}/bin/kill -HUP $MAINPID";
    };
  };
  
  # Frontend service
  systemd.services.cortex-frontend = {
    description = "Cortex Frontend Service";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    
    serviceConfig = {
      Type = "simple";
      Restart = "always";
      RestartSec = "10s";
      User = "nexus";
      Group = "nexus";
      WorkingDirectory = "${projectRoot}/frontend";
      EnvironmentFile = "/etc/cortex/cortex.env";
      Environment = [
        "NODE_ENV=production"
        "PATH=${pkgs.nodejs_20}/bin:${pkgs.nodePackages.pnpm}/bin:$PATH"
      ];
      ExecStart = "${pkgs.bash}/bin/bash -c 'cd ${projectRoot}/frontend && ${pkgs.nodePackages.pnpm}/bin/pnpm preview --host 0.0.0.0 --port 5173'";
      ExecReload = "${pkgs.coreutils}/bin/kill -HUP $MAINPID";
    };
  };
  
  # PostgreSQL service with pgvector
  services.postgresql = {
    enable = true;
    package = pkgs.postgresql_16;
    enableTCPIP = true;
    authentication = pkgs.lib.mkOverride 10 ''
      local all all trust
      host all all 127.0.0.1/32 trust
      host all all ::1/128 trust
    '';
    initialScript = pkgs.writeText "postgresql-init.sql" ''
      CREATE DATABASE argos;
      CREATE USER argos WITH PASSWORD 'argos';
      GRANT ALL PRIVILEGES ON DATABASE argos TO argos;
      \c argos;
      CREATE EXTENSION IF NOT EXISTS pgvector;
      CREATE EXTENSION IF NOT EXISTS uuid_ossp;
    '';
    settings = {
      shared_preload_libraries = "pgvector";
      listen_addresses = "*";
      port = 5432;
    };
  };

  # Docker compose service for Qdrant
  systemd.services.cortex-docker = {
    description = "Cortex Docker Services (Qdrant, etc.)";
    wantedBy = [ "multi-user.target" ];
    requires = [ "docker.service" ];
    after = [ "network.target" "docker.service" ];

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "nexus";
      Group = "nexus";
      WorkingDirectory = projectRoot;
      Environment = [
        "PATH=${pkgs.docker}/bin:${pkgs.docker-compose}/bin:$PATH"
      ];
      ExecStart = "${pkgs.docker-compose}/bin/docker-compose -f ${projectRoot}/ops/docker-compose.yml up -d";
      ExecStop = "${pkgs.docker-compose}/bin/docker-compose -f ${projectRoot}/ops/docker-compose.yml down";
    };
  };
}

