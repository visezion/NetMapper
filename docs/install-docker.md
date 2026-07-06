# Install with netbox-docker

This is the easiest supported deployment path.

## 1. Prepare the server

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git docker.io docker-compose-v2 curl nano
sudo systemctl enable docker
sudo systemctl enable containerd
sudo systemctl start docker
sudo usermod -aG docker "$USER"
newgrp docker
```

## 2. Clone the repositories side by side

```bash
mkdir -p ~/netbox-lab
cd ~/netbox-lab
git clone https://github.com/netbox-community/netbox-docker.git
git clone https://github.com/visezion/NetMapper.git
```

Expected layout:

```text
~/netbox-lab/netbox-docker
~/netbox-lab/NetMapper
```

## 3. Deploy NetBox with NetMapper

```bash
cd ~/netbox-lab/NetMapper
./scripts/deploy_netbox_docker.sh main
```

What the script does:

- fetches and fast-forwards this repository
- builds a fresh NetBox image with NetMapper installed
- installs `git`, `nmap`, `snmp`, and `ntc-templates`
- recreates NetBox and worker containers
- waits for container health checks
- runs NetMapper asset synchronization

Notes:

- the first startup on a fresh database can take several minutes while NetBox applies migrations and builds its initial cache
- this repository overrides the upstream NetBox healthcheck to allow slower first responses on small lab or VM hosts

## 4. Verify the containers are running

```bash
cd ~/netbox-lab/netbox-docker
docker compose ps
```

If you want Docker to keep the stack running after reboot, apply a restart policy:

```bash
docker update --restart unless-stopped $(docker ps -aq)
```

## 5. Deploy when your paths differ

```bash
cd /path/to/NetMapper
NETBOX_DOCKER_DIR=/path/to/netbox-docker \
NETMAPPER_PATH=/path/to/NetMapper \
./scripts/deploy_netbox_docker.sh main
```

## 6. Deploy from a dirty tree for development only

```bash
ALLOW_DIRTY=1 ./scripts/deploy_netbox_docker.sh main
```

## Best full command sequence

For a beginner-friendly end-to-end setup on a new Ubuntu host:

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

cd ~/netbox-lab/netbox-docker
docker compose ps
docker update --restart unless-stopped $(docker ps -aq)
```
