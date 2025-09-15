/**
 * Easter Egg Utilities
 *
 * Utilities for generating and verifying the easter egg key sequence.
 * The classic pattern from 1986 gaming culture.
 */

/**
 * Generate SHA-256 hash for a given string
 * @param {string} str - String to hash
 * @returns {Promise<string>} Hex encoded hash
 */
export async function generateHash(str) {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * The classic gaming pattern from 1986
 * This is the famous Konami Code sequence
 */
export const CLASSIC_PATTERN = [
  "ArrowUp",
  "ArrowUp",
  "ArrowDown",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowLeft",
  "ArrowRight",
  "KeyB",
  "KeyA",
  "Enter",
];

/**
 * Generate the hash for the classic pattern
 * This is used to verify the sequence without storing the actual keys
 */
export async function generateClassicHash() {
  const sequenceString = CLASSIC_PATTERN.join("");
  return await generateHash(sequenceString);
}

/**
 * Development utility to get the expected hash
 * Only available in development mode
 */
export async function getExpectedHash() {
  if (process.env.NODE_ENV === "development") {
    const hash = await generateClassicHash();
    console.log("Expected hash for classic pattern:", hash);
    console.log("Classic pattern:", CLASSIC_PATTERN);
    return hash;
  }
  return null;
}

/**
 * Verify if a key sequence matches the classic pattern
 * @param {Array<string>} sequence - Array of key codes
 * @returns {Promise<boolean>} True if sequence matches
 */
export async function verifyClassicSequence(sequence) {
  if (sequence.length !== CLASSIC_PATTERN.length) {
    return false;
  }

  try {
    const sequenceString = sequence.join("");
    const hash = await generateHash(sequenceString);
    const expectedHash = await generateClassicHash();
    return hash === expectedHash;
  } catch (error) {
    console.warn("Hash verification failed:", error);
    return false;
  }
}

/**
 * Get hints for the easter egg (cryptic but discoverable)
 */
export function getEasterEggHints() {
  return {
    console: "₿ Some secrets are earned... 🎮",
    footer: "Est. 1986",
    code: "1986... some things never change",
    pattern: "↑↑↓↓ is just the beginning",
    gaming: "Patterns from gaming's golden age still hold power",
  };
}

/**
 * Development helper to test the easter egg
 * Only works in development mode
 */
export function debugEasterEgg() {
  if (process.env.NODE_ENV === "development") {
    console.log("🎮 Easter Egg Debug Information:");
    console.log("Pattern length:", CLASSIC_PATTERN.length);
    console.log("Pattern:", CLASSIC_PATTERN);

    // Generate and log the hash
    generateClassicHash().then((hash) => {
      console.log("Expected hash:", hash);
    });

    const hints = getEasterEggHints();
    console.log("Hints:", hints);

    return {
      pattern: CLASSIC_PATTERN,
      hints,
    };
  }

  return null;
}

// Export for development debugging
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  window.debugEasterEgg = debugEasterEgg;
  window.getExpectedHash = getExpectedHash;
}
