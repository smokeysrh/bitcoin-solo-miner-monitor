<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Network Topology</h1>
      </v-col>
    </v-row>

    <!-- Network Controls -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Network Controls</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="layoutType"
                  :items="layoutOptions"
                  item-title="text"
                  item-value="value"
                  label="Layout Type"
                  @change="updateNetworkLayout"
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6">
                <v-btn-toggle
                  v-model="groupByType"
                  mandatory
                  @change="updateNetworkLayout"
                >
                  <v-btn :value="true"> Group by Type </v-btn>
                  <v-btn :value="false"> No Grouping </v-btn>
                </v-btn-toggle>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-btn
                  color="primary"
                  @click="refreshNetwork"
                  :loading="loading"
                >
                  <v-icon left>mdi-refresh</v-icon>
                  Refresh Network
                </v-btn>
                <v-btn
                  class="ml-2"
                  color="secondary"
                  @click="exportNetworkImage"
                >
                  <v-icon left>mdi-download</v-icon>
                  Export Image
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Network Statistics</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="6">
                <div class="text-subtitle-1">Total Miners:</div>
                <div class="text-h5">{{ miners.length }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-1">Online Miners:</div>
                <div class="text-h5">{{ onlineMiners.length }}</div>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="6">
                <div class="text-subtitle-1">Offline Miners:</div>
                <div class="text-h5">{{ offlineMiners.length }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-1">Total Hashrate:</div>
                <div class="text-h5">{{ formatHashrate(totalHashrate) }}</div>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <div class="text-subtitle-1">Miner Types:</div>
                <v-chip-group>
                  <v-chip
                    v-for="(count, type) in minerTypeCount"
                    :key="type"
                    :color="getMinerTypeColor(type)"
                    text-color="white"
                  >
                    {{ type }}: {{ count }}
                  </v-chip>
                </v-chip-group>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Network Visualization -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Network Visualization</v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 600px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="miners.length === 0"
              class="d-flex justify-center align-center"
              style="height: 600px"
            >
              <p class="text-subtitle-1">No miners found in the network</p>
            </div>
            <div
              v-else
              id="network-container"
              style="height: 600px; border: 1px solid #ccc"
            ></div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Miner Details Dialog -->
    <v-dialog v-model="showMinerDetails" max-width="600px">
      <v-card v-if="selectedMiner">
        <v-card-title>
          {{
            selectedMiner.name ||
            `${selectedMiner.type} (${selectedMiner.ip_address})`
          }}
          <v-spacer></v-spacer>
          <v-chip :color="getStatusColor(selectedMiner.status)" dark small>
            {{ selectedMiner.status }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <v-simple-table>
            <template v-slot:default>
              <tbody>
                <tr>
                  <td><strong>ID:</strong></td>
                  <td>{{ selectedMiner.id }}</td>
                </tr>
                <tr>
                  <td><strong>Type:</strong></td>
                  <td>{{ selectedMiner.type }}</td>
                </tr>
                <tr>
                  <td><strong>IP Address:</strong></td>
                  <td>{{ selectedMiner.ip_address }}</td>
                </tr>
                <tr>
                  <td><strong>Port:</strong></td>
                  <td>{{ selectedMiner.port || "Default" }}</td>
                </tr>
                <tr>
                  <td><strong>Hashrate:</strong></td>
                  <td>{{ formatHashrate(selectedMiner.hashrate) }}</td>
                </tr>
                <tr>
                  <td><strong>Temperature:</strong></td>
                  <td>{{ formatTemperature(selectedMiner.temperature) }}</td>
                </tr>
                <tr>
                  <td><strong>Uptime:</strong></td>
                  <td>{{ formatUptime(selectedMiner.uptime) }}</td>
                </tr>
                <tr>
                  <td><strong>Last Seen:</strong></td>
                  <td>{{ formatDate(selectedMiner.last_seen) }}</td>
                </tr>
              </tbody>
            </template>
          </v-simple-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" :to="`/miners/${selectedMiner.id}`">
            View Details
          </v-btn>
          <v-btn color="error" @click="showMinerDetails = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore } from "../stores/settings";
import { formatTemperature } from "../utils/formatters";
import * as d3 from "d3";

export default {
  name: "Network",

  setup() {
    const minersStore = useMinersStore();
    const settingsStore = useSettingsStore();

    // Network visualization
    let networkSimulation = null;
    let networkSvg = null;

    // State
    const loading = ref(false);
    const layoutType = ref("force");
    const groupByType = ref(true);
    const showMinerDetails = ref(false);
    const selectedMiner = ref(null);

    // Layout options
    const layoutOptions = [
      { text: "Force-Directed", value: "force" },
      { text: "Radial", value: "radial" },
      { text: "Grid", value: "grid" },
      { text: "Tree", value: "tree" },
    ];

    // Refresh interval
    let refreshInterval = null;

    // Computed properties
    const miners = computed(() => minersStore.miners);
    const onlineMiners = computed(() => minersStore.onlineMiners);
    const offlineMiners = computed(() => minersStore.offlineMiners);
    const totalHashrate = computed(() => minersStore.totalHashrate);

    const minerTypeCount = computed(() => {
      const counts = {};
      miners.value.forEach((miner) => {
        counts[miner.type] = (counts[miner.type] || 0) + 1;
      });
      return counts;
    });

    // Methods
    const formatHashrate = (hashrate) => {
      if (!hashrate) return "0 H/s";

      const units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s"];
      let unitIndex = 0;

      while (hashrate >= 1000 && unitIndex < units.length - 1) {
        hashrate /= 1000;
        unitIndex++;
      }

      return `${hashrate.toFixed(2)} ${units[unitIndex]}`;
    };

    const formatUptime = (seconds) => {
      if (!seconds) return "N/A";

      const days = Math.floor(seconds / 86400);
      const hours = Math.floor((seconds % 86400) / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);

      let result = "";
      if (days > 0) result += `${days}d `;
      if (hours > 0 || days > 0) result += `${hours}h `;
      result += `${minutes}m`;

      return result;
    };

    const formatDate = (dateString) => {
      if (!dateString) return "N/A";

      const date = new Date(dateString);
      return date.toLocaleString();
    };

    const getStatusColor = (status) => {
      switch (status) {
        case "online":
          return "success";
        case "offline":
          return "error";
        case "restarting":
          return "warning";
        case "error":
          return "error";
        default:
          return "grey";
      }
    };

    const getMinerTypeColor = (type) => {
      switch (type.toLowerCase()) {
        case "bitaxe":
          return "#1976D2"; // Blue
        case "avalon_nano":
          return "#43A047"; // Green
        case "magic_miner":
          return "#E53935"; // Red
        default:
          return "#9C27B0"; // Purple
      }
    };

    const refreshNetwork = async () => {
      loading.value = true;

      try {
        await minersStore.fetchMiners();
        updateNetworkVisualization();
      } catch (error) {
        console.error("Error refreshing network:", error);
      } finally {
        loading.value = false;
      }
    };

    const updateNetworkLayout = () => {
      updateNetworkVisualization();
    };

    const updateNetworkVisualization = () => {
      // Clear previous visualization
      if (networkSvg) {
        d3.select("#network-container").selectAll("*").remove();
      }

      // Create network visualization
      createNetworkVisualization();
    };

    const createNetworkVisualization = () => {
      // Get container dimensions
      const container = document.getElementById("network-container");
      if (!container) return;

      const width = container.clientWidth;
      const height = container.clientHeight;

      // Create SVG
      networkSvg = d3
        .select("#network-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

      // Create nodes and links
      const nodes = [];
      const links = [];

      // Add router node
      nodes.push({
        id: "router",
        name: "Network Router",
        type: "router",
        status: "online",
      });

      // Add miner nodes
      miners.value.forEach((miner) => {
        nodes.push({
          id: miner.id,
          name: miner.name || `${miner.type} (${miner.ip_address})`,
          type: miner.type,
          status: miner.status,
          data: miner,
        });

        // Add link to router
        links.push({
          source: "router",
          target: miner.id,
          value: 1,
        });
      });

      // Create simulation based on layout type
      switch (layoutType.value) {
        case "force":
          createForceLayout(nodes, links, width, height);
          break;
        case "radial":
          createRadialLayout(nodes, links, width, height);
          break;
        case "grid":
          createGridLayout(nodes, links, width, height);
          break;
        case "tree":
          createTreeLayout(nodes, links, width, height);
          break;
        default:
          createForceLayout(nodes, links, width, height);
      }
    };

    const createForceLayout = (nodes, links, width, height) => {
      // Create simulation
      networkSimulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(100),
        )
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(50));

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => Math.sqrt(d.value));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .on("click", handleNodeClick);

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => (d.type === "router" ? 25 : 15))
        .attr("fill", (d) => {
          if (d.type === "router") return "#FFC107";
          return d.status === "online" ? getMinerTypeColor(d.type) : "#9E9E9E";
        })
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5);

      // Add icons to nodes
      node
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("fill", "#fff")
        .text((d) => {
          if (d.type === "router") return "🌐";
          switch (d.type.toLowerCase()) {
            case "bitaxe":
              return "⛏️";
            case "avalon_nano":
              return "🔌";
            case "magic_miner":
              return "✨";
            default:
              return "💻";
          }
        });

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 30)
        .attr("text-anchor", "middle")
        .text((d) => {
          if (d.type === "router") return "Router";
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        })
        .attr("font-size", "12px");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const createRadialLayout = (nodes, links, width, height) => {
      // Group nodes by type if needed
      const groupedNodes = [...nodes];

      if (groupByType.value) {
        // Create hierarchy
        const typeGroups = {};
        nodes.forEach((node) => {
          if (node.type !== "router") {
            if (!typeGroups[node.type]) {
              typeGroups[node.type] = [];
            }
            typeGroups[node.type].push(node);
          }
        });

        // Position nodes in circles around their type
        const radius = Math.min(width, height) / 3;
        const centerX = width / 2;
        const centerY = height / 2;

        // Position router at center
        const router = nodes.find((n) => n.type === "router");
        if (router) {
          router.x = centerX;
          router.y = centerY;
          router.fx = centerX;
          router.fy = centerY;
        }

        // Position type groups in a circle around the router
        const typeKeys = Object.keys(typeGroups);
        typeKeys.forEach((type, i) => {
          const angle = (i / typeKeys.length) * 2 * Math.PI;
          const groupX = centerX + radius * Math.cos(angle);
          const groupY = centerY + radius * Math.sin(angle);

          // Position nodes in a smaller circle around their type center
          const nodesInGroup = typeGroups[type];
          const groupRadius = 50;

          nodesInGroup.forEach((node, j) => {
            const nodeAngle = (j / nodesInGroup.length) * 2 * Math.PI;
            node.x = groupX + groupRadius * Math.cos(nodeAngle);
            node.y = groupY + groupRadius * Math.sin(nodeAngle);
          });
        });
      }

      // Create force simulation
      networkSimulation = d3
        .forceSimulation(groupedNodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(100),
        )
        .force("charge", d3.forceManyBody().strength(-100))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(30));

      if (groupByType.value) {
        // Fix router position
        const router = groupedNodes.find((n) => n.type === "router");
        if (router) {
          router.fx = width / 2;
          router.fy = height / 2;
        }
      }

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => Math.sqrt(d.value));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(groupedNodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .on("click", handleNodeClick);

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => (d.type === "router" ? 25 : 15))
        .attr("fill", (d) => {
          if (d.type === "router") return "#FFC107";
          return d.status === "online" ? getMinerTypeColor(d.type) : "#9E9E9E";
        })
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5);

      // Add icons to nodes
      node
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("fill", "#fff")
        .text((d) => {
          if (d.type === "router") return "🌐";
          switch (d.type.toLowerCase()) {
            case "bitaxe":
              return "⛏️";
            case "avalon_nano":
              return "🔌";
            case "magic_miner":
              return "✨";
            default:
              return "💻";
          }
        });

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 30)
        .attr("text-anchor", "middle")
        .text((d) => {
          if (d.type === "router") return "Router";
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        })
        .attr("font-size", "12px");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        if (d.type !== "router" || !groupByType.value) {
          d.fx = null;
          d.fy = null;
        }
      }
    };

    const createGridLayout = (nodes, links, width, height) => {
      // Calculate grid dimensions
      const totalNodes = nodes.length;
      const cols = Math.ceil(Math.sqrt(totalNodes));
      const rows = Math.ceil(totalNodes / cols);

      const cellWidth = width / (cols + 1);
      const cellHeight = height / (rows + 1);

      // Position nodes in grid
      nodes.forEach((node, i) => {
        const row = Math.floor(i / cols);
        const col = i % cols;

        node.x = (col + 1) * cellWidth;
        node.y = (row + 1) * cellHeight;

        // Fix router position
        if (node.type === "router") {
          node.x = width / 2;
          node.y = height / 4;
        }
      });

      // Create force simulation with very weak forces
      networkSimulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(100)
            .strength(0.1),
        )
        .force("charge", d3.forceManyBody().strength(-10))
        .force("center", d3.forceCenter(width / 2, height / 2).strength(0.1))
        .force(
          "x",
          d3
            .forceX()
            .x((d) => d.x)
            .strength(0.7),
        )
        .force(
          "y",
          d3
            .forceY()
            .y((d) => d.y)
            .strength(0.7),
        );

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => Math.sqrt(d.value));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .on("click", handleNodeClick);

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => (d.type === "router" ? 25 : 15))
        .attr("fill", (d) => {
          if (d.type === "router") return "#FFC107";
          return d.status === "online" ? getMinerTypeColor(d.type) : "#9E9E9E";
        })
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5);

      // Add icons to nodes
      node
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("fill", "#fff")
        .text((d) => {
          if (d.type === "router") return "🌐";
          switch (d.type.toLowerCase()) {
            case "bitaxe":
              return "⛏️";
            case "avalon_nano":
              return "🔌";
            case "magic_miner":
              return "✨";
            default:
              return "💻";
          }
        });

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 30)
        .attr("text-anchor", "middle")
        .text((d) => {
          if (d.type === "router") return "Router";
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        })
        .attr("font-size", "12px");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const createTreeLayout = (nodes, links, width, height) => {
      // Create hierarchy data
      const routerNode = nodes.find((n) => n.type === "router");
      if (!routerNode) return;

      // Group miners by type if needed
      if (groupByType.value) {
        // Create hierarchy
        const hierarchy = {
          id: "router",
          name: "Network Router",
          type: "router",
          status: "online",
          children: [],
        };

        // Group by type
        const typeGroups = {};
        nodes.forEach((node) => {
          if (node.type !== "router") {
            if (!typeGroups[node.type]) {
              typeGroups[node.type] = [];
            }
            typeGroups[node.type].push(node);
          }
        });

        // Add type groups to hierarchy
        Object.entries(typeGroups).forEach(([type, minerNodes]) => {
          const typeNode = {
            id: `type-${type}`,
            name: type,
            type: "group",
            children: minerNodes.map((miner) => ({
              ...miner,
              children: [],
            })),
          };
          hierarchy.children.push(typeNode);
        });

        // Create tree layout
        const treeLayout = d3.tree().size([width - 100, height - 100]);

        // Create hierarchy
        const root = d3.hierarchy(hierarchy);

        // Apply layout
        const treeData = treeLayout(root);

        // Extract nodes and links
        const treeNodes = [];
        const treeLinks = [];

        // Add nodes
        treeData.descendants().forEach((d) => {
          const node = {
            id: d.data.id,
            name: d.data.name,
            type: d.data.type,
            status: d.data.status,
            data: d.data.data,
            x: d.x + 50,
            y: d.y + 50,
          };
          treeNodes.push(node);
        });

        // Add links
        treeData.links().forEach((d) => {
          treeLinks.push({
            source: d.source.data.id,
            target: d.target.data.id,
            value: 1,
          });
        });

        // Create force simulation with very weak forces
        networkSimulation = d3
          .forceSimulation(treeNodes)
          .force(
            "link",
            d3
              .forceLink(treeLinks)
              .id((d) => d.id)
              .distance(100)
              .strength(0.1),
          )
          .force("charge", d3.forceManyBody().strength(-10))
          .force(
            "x",
            d3
              .forceX()
              .x((d) => d.x)
              .strength(0.9),
          )
          .force(
            "y",
            d3
              .forceY()
              .y((d) => d.y)
              .strength(0.9),
          );

        // Create links
        const link = networkSvg
          .append("g")
          .selectAll("line")
          .data(treeLinks)
          .enter()
          .append("line")
          .attr("stroke", "#999")
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", (d) => Math.sqrt(d.value));

        // Create nodes
        const node = networkSvg
          .append("g")
          .selectAll("g")
          .data(treeNodes)
          .enter()
          .append("g")
          .call(
            d3
              .drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended),
          )
          .on("click", handleNodeClick);

        // Add circles to nodes
        node
          .append("circle")
          .attr("r", (d) => {
            if (d.type === "router") return 25;
            if (d.type === "group") return 20;
            return 15;
          })
          .attr("fill", (d) => {
            if (d.type === "router") return "#FFC107";
            if (d.type === "group") return "#673AB7";
            return d.status === "online"
              ? getMinerTypeColor(d.type)
              : "#9E9E9E";
          })
          .attr("stroke", "#fff")
          .attr("stroke-width", 1.5);

        // Add icons to nodes
        node
          .append("text")
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "central")
          .attr("fill", "#fff")
          .text((d) => {
            if (d.type === "router") return "🌐";
            if (d.type === "group") return "📁";
            switch (d.type.toLowerCase()) {
              case "bitaxe":
                return "⛏️";
              case "avalon_nano":
                return "🔌";
              case "magic_miner":
                return "✨";
              default:
                return "💻";
            }
          });

        // Add labels to nodes
        node
          .append("text")
          .attr("dy", 30)
          .attr("text-anchor", "middle")
          .text((d) => {
            if (d.type === "router") return "Router";
            if (d.type === "group") return d.name;
            return d.name.length > 15
              ? `${d.name.substring(0, 12)}...`
              : d.name;
          })
          .attr("font-size", "12px");

        // Update positions on tick
        networkSimulation.on("tick", () => {
          link
            .attr("x1", (d) => d.source.x)
            .attr("y1", (d) => d.source.y)
            .attr("x2", (d) => d.target.x)
            .attr("y2", (d) => d.target.y);

          node.attr("transform", (d) => `translate(${d.x},${d.y})`);
        });
      } else {
        // Simple tree without grouping
        createRadialLayout(nodes, links, width, height);
      }

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const handleNodeClick = (event, d) => {
      // Only show details for miner nodes
      if (d.type !== "router" && d.type !== "group" && d.data) {
        selectedMiner.value = d.data;
        showMinerDetails.value = true;
      }
    };

    const exportNetworkImage = () => {
      // Get SVG element
      const svgElement = document.querySelector("#network-container svg");
      if (!svgElement) return;

      // Create a canvas element
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      // Set canvas dimensions
      canvas.width = svgElement.clientWidth;
      canvas.height = svgElement.clientHeight;

      // Create an image from the SVG
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const img = new Image();

      // Create a Blob from the SVG data
      const svgBlob = new Blob([svgData], {
        type: "image/svg+xml;charset=utf-8",
      });
      const url = URL.createObjectURL(svgBlob);

      // When the image is loaded, draw it on the canvas and download
      img.onload = () => {
        // Fill background
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);

        // Draw SVG on canvas
        context.drawImage(img, 0, 0);

        // Convert canvas to data URL
        const dataUrl = canvas.toDataURL("image/png");

        // Create download link
        const link = document.createElement("a");
        link.download = "network_topology.png";
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up
        URL.revokeObjectURL(url);
      };

      img.src = url;
    };

    // Lifecycle hooks
    onMounted(async () => {
      // Fetch miners
      await minersStore.fetchMiners();

      // Create network visualization
      createNetworkVisualization();

      // Set up refresh interval
      const refreshTime = settingsStore.settings.refresh_interval * 1000 * 5; // Less frequent than dashboard
      refreshInterval = setInterval(async () => {
        await refreshNetwork();
      }, refreshTime);
    });

    onUnmounted(() => {
      // Clear refresh interval
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }

      // Stop simulation
      if (networkSimulation) {
        networkSimulation.stop();
      }
    });

    return {
      // State
      loading,
      layoutType,
      layoutOptions,
      groupByType,
      showMinerDetails,
      selectedMiner,

      // Computed
      miners,
      onlineMiners,
      offlineMiners,
      totalHashrate,
      minerTypeCount,

      // Methods
      formatHashrate,
      formatTemperature,
      formatUptime,
      formatDate,
      getStatusColor,
      getMinerTypeColor,
      refreshNetwork,
      updateNetworkLayout,
      exportNetworkImage,
    };
  },
};
</script>
