# NetDoc: an automatic Network Documentation plugin for NetBox

NetDoc is an automatic network documentation plugin for [NetBox](https://github.com/netbox-community/netbox "NetBox"). NetDoc aims to discover a partially known network populating netbox and drawing L2 and L3 diagrams.

NetDoc would be the industrialized, open-source tool available to the public to discover multi-vendor networks.

Compatibility:

* The current repository is being updated for NetBox 4.6.x.
* Historical NetDoc 3.5.x targeted NetBox 3.5.x.
* Historical NetDoc 0.10.x targeted NetBox 3.4.x.

## Server deploy flow

When deploying with `netbox-docker`, make sure the server updates the NetDoc repository before starting the image build. A simple server-side flow is:

```bash
cd /path/to/netdoc
./scripts/deploy_netbox_docker.sh
```

The script:

* runs `git fetch --all --prune`
* updates the checked out branch using `git pull --ff-only`
* prints the exact Git commit being deployed
* refuses to deploy from a dirty working tree by default
* validates the built image can import the expected patched `netdoc`
* rebuilds the NetBox plugin image with `--no-cache`
* restarts `netbox`, `netbox-worker`, and `netbox-housekeeping`
* prints the latest `netbox` container logs

If you want to deploy a specific branch, pass it as the first argument:

```bash
./scripts/deploy_netbox_docker.sh main
```

If the server intentionally has uncommitted local changes, you can override the dirty-tree safety check:

```bash
ALLOW_DIRTY=1 ./scripts/deploy_netbox_docker.sh
```

## Table of contents

1. [Introduction](https://github.com/dainok/netdoc/wiki "Introduction")
1. [Device configuration](https://github.com/dainok/netdoc/wiki/Device-configuration "Device configuration")
1. [NetBox with NetDoc installation](https://github.com/dainok/netdoc/wiki/NetBox-with-NetDoc-installation "NetBox with NetDoc installation")
1. [Utilizing NetDoc](https://github.com/dainok/netdoc/wiki/Utilizing-NetDoc "Utilizing NetDoc")
1. [Developing NetDoc](https://github.com/dainok/netdoc/wiki/Developing-NetDoc "Developing NetDoc")
1. [Frequently Asked Questions and Errors](https://github.com//dainok/netdoc/wiki/Developing-NetDoc "Frequently Asked Questions and Errors")
