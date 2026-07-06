# Overview

## Maintainer

- Name: Victor Ayodeji Oluwasusi
- Email: oluwasusiv@gmail.com
- Repository: `https://github.com/visezion/NetMapper`

## Compatibility

This repository has been updated and validated against:

- NetBox `4.6.4`
- `netbox-docker` `5.0.1`
- plugin package name `netmapper`

Deployment targets covered by this repository:

- `netbox-docker`
- standard NetBox Python installations

## Features

NetMapper currently provides:

- multi-vendor discovery through Nornir and Netmiko
- Palo Alto XML API discovery support
- VMware vSphere inventory discovery support
- discoverable device management inside NetBox
- discovery job execution and logging
- parsed command ingestion into NetBox models
- ARP, MAC address table, and routing table ingestion
- L2, L3, and site diagrams inside NetBox
- subnet/range scanning with `nmap`
- optional SNMP-assisted platform inference during scans
- stored SNMP credentials in the UI
- scan preview, dry-run, and scan history
- credential test pages for discovery and SNMP credentials
- persistent scan identity notes stored on discoverables

## Supported Discovery Modes

The current discovery mode set includes:

- Allied Telesis AW+
- Aruba AOS-CX
- Cisco IOS XE
- Cisco IOS XE over Telnet
- Cisco NX-OS
- Cisco XR
- HPE Comware
- HPE ProCurve
- HPE ProCurve over Telnet
- Huawei VRP
- Linux
- Palo Alto Networks NGFW via XML API
- VMware vSphere
