/*
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"
 */

function htmlTitle(html) {
    // Convert HTML in node's title to a document DIV
    container = document.createElement("div");
    container.innerHTML = html;
    return container;
  }

var graph;
var activeGroupDrag = null;
var topologyData;
var topologyDetails;
var groupMemberMap = {};

function buildGroupMemberMap(nodes) {
    var groupMemberMap = {};
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes[i];
        if (!node["location_group_key"] || node["group_anchor"]) {
            continue;
        }
        var groupNodeId = "group::" + node["location_group_key"];
        if (!(groupNodeId in groupMemberMap)) {
            groupMemberMap[groupNodeId] = [];
        }
        groupMemberMap[groupNodeId].push(node["id"]);
    }
    return groupMemberMap;
}

function startGroupDrag(groupNodeId, groupMemberMap) {
    if (!(groupNodeId in groupMemberMap)) {
        activeGroupDrag = null;
        return;
    }

    activeGroupDrag = {
        groupNodeId: groupNodeId,
        memberIds: groupMemberMap[groupNodeId],
        groupStartPosition: graph.getPositions([groupNodeId])[groupNodeId],
        memberStartPositions: graph.getPositions(groupMemberMap[groupNodeId]),
    };
}

function updateGroupDragPosition() {
    if (!activeGroupDrag) {
        return;
    }

    var currentGroupPosition = graph.getPositions([activeGroupDrag.groupNodeId])[activeGroupDrag.groupNodeId];
    if (!currentGroupPosition || !activeGroupDrag.groupStartPosition) {
        return;
    }

    var deltaX = currentGroupPosition["x"] - activeGroupDrag.groupStartPosition["x"];
    var deltaY = currentGroupPosition["y"] - activeGroupDrag.groupStartPosition["y"];

    for (var i = 0; i < activeGroupDrag.memberIds.length; i++) {
        var memberId = activeGroupDrag.memberIds[i];
        var startPosition = activeGroupDrag.memberStartPositions[memberId];
        if (!startPosition) {
            continue;
        }
        graph.moveNode(memberId, startPosition["x"] + deltaX, startPosition["y"] + deltaY);
    }
}

function stopGroupDrag() {
    if (!activeGroupDrag) {
        return;
    }
    updateGroupDragPosition();
    activeGroupDrag = null;
}

function isClusterEnabled() {
    return !("group_clusters" in topologyDetails) || topologyDetails["group_clusters"] !== false;
}

function getRenderableTopologyData() {
    if (isClusterEnabled()) {
        return {
            "nodes": topologyData["nodes"].map(function (node) {
                return Object.assign({}, node);
            }),
            "edges": topologyData["edges"].map(function (edge) {
                return Object.assign({}, edge);
            }),
        };
    }

    return {
        "nodes": topologyData["nodes"].filter(function (node) {
            return !node["group_anchor"];
        }).map(function (node) {
            return Object.assign({}, node);
        }),
        "edges": topologyData["edges"].filter(function (edge) {
            return !edge["hidden"];
        }).map(function (edge) {
            return Object.assign({}, edge);
        }),
    };
}

function decodeTopologyTitles(renderableTopologyData) {
    for (var i = 0; i < renderableTopologyData["nodes"].length; i++) {
        renderableTopologyData["nodes"][i]["title"] = htmlTitle(renderableTopologyData["nodes"][i]["title"]);
    }
    for (var j = 0; j < renderableTopologyData["edges"].length; j++) {
        renderableTopologyData["edges"][j]["title"] = htmlTitle(renderableTopologyData["edges"][j]["title"]);
    }
}

function bindGraphEvents() {
    graph.on("afterDrawing", saveNodePositionsOnce);
    graph.on("dragStart", function (event) {
        if (!isClusterEnabled() || !event.nodes || event.nodes.length !== 1) {
            activeGroupDrag = null;
            return;
        }
        var selectedNodeId = event.nodes[0];
        if (String(selectedNodeId).startsWith("group::")) {
            startGroupDrag(selectedNodeId, groupMemberMap);
        } else {
            activeGroupDrag = null;
        }
    });
    graph.on("dragging", function () {
        if (isClusterEnabled()) {
            updateGroupDragPosition();
        }
    });
    graph.on("dragEnd", function () {
        if (isClusterEnabled()) {
            stopGroupDrag();
        }
    });
}

function renderGraph() {
    var renderableTopologyData = getRenderableTopologyData();
    var container = document.getElementById("visgraph");

    decodeTopologyTitles(renderableTopologyData);

    if (graph) {
        graph.destroy();
    }

    groupMemberMap = buildGroupMemberMap(renderableTopologyData["nodes"]);
    graph = new vis.Network(container, renderableTopologyData, visGraphOptions(topologyDetails["physics"]));
    graph.fit();
    bindGraphEvents();
}

// VisGraph options
function visGraphOptions(physics) {
    var options = {
        interaction: {
            hover: true,
            hoverConnectedEdges: true,
            multiselect: true,
        },
        nodes: {
            shape: 'image',
            size: 35,
            font: {
                multi: "md",
                face: "helvetica",
                color:
                    document.documentElement.dataset.netboxColorMode === "dark"
                        ? "#ffffff"
                        : "#000000",
            },
        },
        edges: {
            length: 100,
            width: 2,
            font: {
                face: "helvetica",
            },
            shadow: {
                enabled: true,
            },
        },
        physics: {
            enabled: physics,
            solver: "forceAtlas2Based",
        },
    }
    return options
}

// Set diagram toggle mode button
function setBtnToggleDiagram(physics) {
    var btnToggleDiagramMode = document.getElementById("btnToggleDiagramMode");
    if (physics) {
        btnToggleDiagramMode.innerHTML = '<i class="mdi mdi-pin"></i> Static';
    } else {
        btnToggleDiagramMode.innerHTML = '<i class="mdi mdi-pin-off"></i> Dynamic';
    }
}

// Get current diagram_id
function getDiagramId() {
    var url = new URL(document.URL);
    var diagram_id = url.pathname.split("/")[4]
    return diagram_id;
}

// Save node positions
function saveNodePositions() {
    // Load CSRF token
    var csrftoken = getCsrfToken();

    var physics = graph.physics.physicsEnabled;
    var diagram_id = getDiagramId();
    var url = "/api/plugins/netmapper/diagram/" + diagram_id + "/";
    var xhr = new XMLHttpRequest();
    xhr.open("PATCH", url);
    xhr.setRequestHeader('X-CSRFToken', csrftoken );
    xhr.setRequestHeader("Accept", "application/json");
    xhr.setRequestHeader("Content-Type", "application/json");

    // Get current data and save
    var data = JSON.stringify({
        "details": {
            "physics": physics,
            "group_clusters": isClusterEnabled(),
            "positions": graph.getPositions(),
        },
    });
    xhr.onload = () => {
        // Request finished
        if (xhr.status >= 200 && xhr.status < 300) {
            addMessage("success", "Diagram has been saved");
        } else {
            addMessage("danger", "Failed to save diagram (HTTP " + xhr.status + ")");
        }
    };
    xhr.onerror = () => {
        addMessage("danger", "Failed to save diagram");
    };
    xhr.send(data);
}

// Save node position and disable trigger
function saveNodePositionsOnce() {
    saveNodePositions();
    graph.off("afterDrawing", saveNodePositionsOnce);
}

// On page load
window.addEventListener("load", () => {
    // Load topology data from Django
    topologyData = JSON.parse(document.getElementById("topology_data_json").textContent);
    topologyDetails = JSON.parse(document.getElementById("topology_details_json").textContent);
    topologyDetails["physics"] = "physics" in topologyDetails ? topologyDetails["physics"] : true;
    topologyDetails["group_clusters"] = !("group_clusters" in topologyDetails) || topologyDetails["group_clusters"] !== false;
    const hasTopology = topologyData["nodes"].length > 0;

    // Set giagram mode button
    setBtnToggleDiagram(topologyDetails["physics"]);

    if (!hasTopology) {
        return;
    }

    renderGraph();

    // On btnToggleDiagramMode click
    document.getElementById("btnToggleDiagramMode").addEventListener("click", (event) => {
        event.preventDefault();
        var new_physics = !graph.physics.physicsEnabled;
        graph.setOptions({ physics: new_physics });
        topologyDetails["physics"] = new_physics;
        // Update button
        setBtnToggleDiagram(new_physics);
    });

    // On btnSaveDiagram click
    document.getElementById("btnSaveDiagram").addEventListener("click", (event) => {
        event.preventDefault();
        saveNodePositions();
    });
});
