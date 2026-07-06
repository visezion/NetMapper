# NetMapper for NetBox 4.6.x

NetMapper is a NetBox plugin for network discovery, topology mapping, operational documentation, and subnet or range seeding.

This repository is maintained as the `visezion/NetMapper` fork and is currently targeted at NetBox `4.6.x`, including `netbox-docker` deployments.

## At a Glance

- NetBox `4.6.4`
- `netbox-docker` `5.0.1`
- plugin package name `netmapper`
- maintained by Victor Ayodeji Oluwasusi

## Quick Links

- [Overview](docs/overview.md)
- [How NetMapper Works](docs/how-it-works.md)
- [Repository Layout](docs/repository-layout.md)
- [Requirements](docs/requirements.md)
- [Install with netbox-docker](docs/install-docker.md)
- [Install into an Existing NetBox Instance](docs/install-standard.md)
- [Configuration](docs/configuration.md)
- [How to Use NetMapper](docs/usage.md)
- [UI Guide](docs/ui-guide.md)
- [Discovery Workflows](docs/discovery-workflows.md)
- [Scan History and Identity Notes](docs/scan-history.md)
- [Diagrams](docs/diagrams.md)
- [Developer Guide](docs/developer-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development and Validation](docs/development.md)
- [Upgrade Notes](docs/upgrade-notes.md)
- [License and Origin](docs/license-origin.md)

## Quick Start

For Docker deployment on Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git docker.io docker-compose-v2 curl nano
sudo systemctl enable docker
sudo systemctl enable containerd
sudo systemctl start docker
sudo usermod -aG docker "$USER"
newgrp docker

mkdir -p ~/netbox-lab
cd ~/netbox-lab
git clone https://github.com/netbox-community/netbox-docker.git
git clone https://github.com/visezion/NetMapper.git

cd ~/netbox-lab/NetMapper
./scripts/deploy_netbox_docker.sh main
```

For the full Docker guide, see [Install with netbox-docker](docs/install-docker.md).
