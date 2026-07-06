# Requirements

## Runtime Requirements

- NetBox `4.6.x`
- Python version matching the target NetBox runtime
- `nmap`
- `snmpget`
- `ntc-templates`

## netbox-docker Prerequisites

For a fresh Ubuntu server using the Docker deployment path, install Docker and the basic tools first:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git docker.io docker-compose-v2 curl nano
sudo systemctl enable docker
sudo systemctl enable containerd
sudo systemctl start docker
sudo usermod -aG docker "$USER"
newgrp docker
```

Notes:

- run `newgrp docker` or start a new shell session before using `docker compose`
- if your distribution uses different package names, install Docker Engine plus the Docker Compose v2 plugin

## Python Requirements

Installed by `setup.py`:

- `netmiko`
- `nornir`
- `nornir_netmiko`
- `nornir_utils`
- `jsonschema`
- `xmltodict`
- `n2g`
- `ouilookup`
- `pyvmomi`
