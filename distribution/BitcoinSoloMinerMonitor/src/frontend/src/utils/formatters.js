/**
 * Utility functions for formatting data display
 */

/**
 * Format temperature to display as whole numbers only
 * @param {number|string} temperature - Temperature value (can be decimal)
 * @returns {string} Formatted temperature string (e.g., "72°C")
 */
export const formatTemperature = (temperature) => {
  // Handle null, undefined, or empty values
  if (temperature === null || temperature === undefined || temperature === '') {
    return 'N/A';
  }

  // Convert to number if it's a string
  const temp = typeof temperature === 'string' ? parseFloat(temperature) : temperature;

  // Handle invalid numbers
  if (isNaN(temp)) {
    return 'N/A';
  }

  // Round to nearest whole number and format
  return `${Math.round(temp)}°C`;
};

/**
 * Format hashrate with appropriate units
 * @param {number} hashrate - Hashrate value in H/s
 * @returns {string} Formatted hashrate string
 */
export const formatHashrate = (hashrate) => {
  if (!hashrate) return "0 H/s";

  const units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s"];
  let unitIndex = 0;
  let value = hashrate;

  while (value >= 1000 && unitIndex < units.length - 1) {
    value /= 1000;
    unitIndex++;
  }

  return `${value.toFixed(2)} ${units[unitIndex]}`;
};