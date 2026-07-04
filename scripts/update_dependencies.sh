#!/bin/bash

wget -O- https://visjs.github.io/vis-network/standalone/umd/vis-network.min.js > netmapper/static/netmapper/js/vis-network.min.js
wget -O- https://visjs.github.io/vis-network/standalone/umd/vis-network.min.js.map > netmapper/static/netmapper/js/vis-network.min.js.map
wget -O- https://visjs.github.io/vis-network/dist/dist/vis-network.min.css > netmapper/static/netmapper/css/vis-network.min.css
