/**
 * Centralized Port Configuration
 *
 * Single source of truth for all port-related defaults across the application.
 * This ensures consistency between setup wizard, network scanner, and backend.
 */

/**
 * Default ports to scan when discovering miners on the network.
 * Includes all common miner types and Bitcoin node ports.
 */
export const DEFAULT_SCAN_PORTS = [
  80, // Bitaxe, Magic Miner web interface
  4028, // Avalon Nano CGMiner API
  8332, // Bitcoin RPC (mainnet)
  18332, // Bitcoin RPC (testnet)
  8333, // Bitcoin P2P (mainnet)
  18333, // Bitcoin P2P (testnet)
  8080, // Alternative web interface
];

/**
 * Default ports for each miner type.
 * Used when adding miners manually or when auto-detecting type.
 */
export const MINER_TYPE_PORTS = {
  bitaxe: 80,
  avalon_nano: 4028,
  magic_miner: 80,
  bitcoin_node: 8332,
};

/**
 * Bitcoin-specific port definitions with descriptions.
 */
export const BITCOIN_PORTS = {
  8332: {
    name: "Bitcoin RPC (Mainnet)",
    description: "Bitcoin Core RPC interface for mainnet",
    protocol: "RPC",
  },
  18332: {
    name: "Bitcoin RPC (Testnet)",
    description: "Bitcoin Core RPC interface for testnet",
    protocol: "RPC",
  },
  8333: {
    name: "Bitcoin P2P (Mainnet)",
    description: "Bitcoin Core peer-to-peer network port for mainnet",
    protocol: "P2P",
  },
  18333: {
    name: "Bitcoin P2P (Testnet)",
    description: "Bitcoin Core peer-to-peer network port for testnet",
    protocol: "P2P",
  },
};

/**
 * Get default port for a miner type.
 * @param {string} minerType - The miner type (e.g., 'bitaxe', 'bitcoin_node')
 * @returns {number} - Default port number
 */
export function getDefaultPort(minerType) {
  return MINER_TYPE_PORTS[minerType] || 80;
}

/**
 * Get formatted port list as string for display.
 * @param {Array<number>} ports - Array of port numbers (optional)
 * @returns {string} - Comma-separated port list
 */
export function formatPortList(ports = DEFAULT_SCAN_PORTS) {
  return ports.join(", ");
}

/**
 * Parse port list from string input.
 * @param {string} portsString - Comma-separated port list
 * @returns {Array<number>} - Array of valid port numbers
 */
export function parsePortList(portsString) {
  if (!portsString || portsString.trim() === "") {
    return DEFAULT_SCAN_PORTS;
  }

  try {
    const ports = portsString
      .split(",")
      .map((p) => p.trim())
      .filter((p) => p !== "")
      .map((p) => parseInt(p))
      .filter((p) => !isNaN(p) && p >= 1 && p <= 65535);

    return ports.length > 0 ? ports : DEFAULT_SCAN_PORTS;
  } catch (error) {
    console.error("Error parsing port list:", error);
    return DEFAULT_SCAN_PORTS;
  }
}

/**
 * Validate a port number.
 * @param {number} port - Port number to validate
 * @returns {boolean} - True if valid
 */
export function isValidPort(port) {
  return Number.isInteger(port) && port >= 1 && port <= 65535;
}

/**
 * Get port description if available.
 * @param {number} port - Port number
 * @returns {string|null} - Port description or null
 */
export function getPortDescription(port) {
  return BITCOIN_PORTS[port]?.description || null;
}

export default {
  DEFAULT_SCAN_PORTS,
  MINER_TYPE_PORTS,
  BITCOIN_PORTS,
  getDefaultPort,
  formatPortList,
  parsePortList,
  isValidPort,
  getPortDescription,
};
