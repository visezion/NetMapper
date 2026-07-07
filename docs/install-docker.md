# Install with netbox-docker

This is the easiest supported deployment path.

Supported target:

- NetBox `4.6.x`
- default pinned image: `netboxcommunity/netbox:v4.6.4`

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
git clone --branch 5.0.1 --depth 1 https://github.com/netbox-community/netbox-docker.git
git clone --branch main --depth 1 https://github.com/visezion/NetMapper.git
```

Why this is pinned:

- without `--branch`, Git clones the current default branch, which can change over time
- these commands pin `netbox-docker` to the tested `5.0.1` release
- NetMapper is intentionally cloned from `main` because the deploy script is designed to track a branch and update from GitHub before each build
- this keeps first-time installs reproducible

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
- uses the pinned NetBox base image `v4.6.4` unless you deliberately override it
- installs `git`, `nmap`, `snmp`, and `ntc-templates`
- links the NetMapper compose override into the `netbox-docker` directory
- recreates NetBox and worker containers
- waits for container health checks
- runs NetMapper asset synchronization
- prints progress messages while NetBox and the worker are still starting

Notes:

- the first startup on a fresh database can take several minutes while NetBox applies migrations and builds its initial cache
- this repository overrides the upstream NetBox healthcheck to allow slower first responses on small lab or VM hosts
- the deploy script creates `netbox-docker/docker-compose.override.yml` as a symlink to NetMapper's override file so future `docker compose up -d` runs continue to use the plugin image
- by default the build now reuses Docker cache for faster repeat deployments; set `BUILD_NO_CACHE=1` when you need a full clean rebuild

## 4. Verify the containers are running

```bash
cd ~/netbox-lab/netbox-docker
docker compose ps
```

If you want Docker to keep the stack running after reboot, apply a restart policy:

```bash
docker update --restart unless-stopped $(docker ps -aq)
```

After that, a normal restart from the `netbox-docker` directory will keep using the NetMapper-enabled image:

```bash
cd ~/netbox-lab/netbox-docker
docker compose up -d
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

## 7. Force a full clean rebuild when needed

```bash
BUILD_NO_CACHE=1 ./scripts/deploy_netbox_docker.sh main
```

## 8. Override the NetBox image version only if you mean to test another 4.6 release

The plugin is intended for NetBox `4.6.x`. The Docker build defaults to `4.6.4`.

```bash
cd ~/netbox-lab/NetMapper
docker compose build --build-arg NETBOX_VERSION=v4.6.4
```

If you change the version, stay within the supported `4.6.x` range unless you are doing development validation.

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
git clone --branch 5.0.1 --depth 1 https://github.com/netbox-community/netbox-docker.git
git clone --branch main --depth 1 https://github.com/visezion/NetMapper.git

cd ~/netbox-lab/NetMapper
./scripts/deploy_netbox_docker.sh main

cd ~/netbox-lab/netbox-docker
docker compose ps
docker update --restart unless-stopped $(docker ps -aq)
```
