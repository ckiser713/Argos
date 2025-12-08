# Systemd overrides for mounts (models, qdrant, logs)

These drop-ins keep services consistent with Compose mounts. Place under `/etc/systemd/system/<unit>.service.d/override.conf` and run `sudo systemctl daemon-reload` afterward.

## cortex-backend.service
```
[Service]
EnvironmentFile=/etc/cortex/cortex.env
BindReadOnlyPaths=/models
BindPaths=/var/lib/cortex/qdrant
BindPaths=/var/log/cortex
```

## cortex-frontend.service
```
[Service]
EnvironmentFile=/etc/cortex/cortex.env
```

## vllm.service (if using the Nix systemd vLLM unit)
```
[Service]
EnvironmentFile=/etc/cortex/cortex.env
BindReadOnlyPaths=/models
BindPaths=/var/log/cortex
DeviceAllow=/dev/kfd rw
DeviceAllow=/dev/dri rw
DeviceAllow=/dev/shm rw
```

## Apply
```
sudo systemctl daemon-reload
sudo systemctl restart cortex-backend cortex-frontend vllm
```
