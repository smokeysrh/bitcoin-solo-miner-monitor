/**
 * Bitcoin Easter Egg Composable
 *
 * Implements a cryptographically secured key sequence detection system
 * with Bitcoin logo rain animation. Respects accessibility preferences.
 *
 * "1986... some things never change" - Classic patterns still hold power
 */

import { ref, onMounted, onUnmounted, computed } from "vue";
// Bitcoin logo utilities removed - will be added after downloading official logos
import {
  verifyClassicSequence,
  getEasterEggHints,
  CLASSIC_PATTERN,
} from "../utils/easterEggUtils.js";

// Cryptographic hash for security - patterns from gaming's golden age
const CLASSIC_PATTERN_LENGTH = CLASSIC_PATTERN.length;

// Animation configuration
const ANIMATION_CONFIG = {
  duration: 15000, // 15 seconds total animation
  logoCount: 25, // Logos per wave
  logoSize: 64, // 64px logos - much larger and more visible
  fallSpeed: {
    min: 2000, // 2 seconds minimum fall time - back to faster speeds
    max: 4000, // 4 seconds maximum fall time - back to faster speeds
  },
  horizontalSpread: 0.8, // Use 80% of viewport width
  rotationSpeed: {
    min: 0.5, // Normal rotation speed
    max: 2.0,
  },
  zIndex: 99999, // Very high z-index to appear above all content including modals
  waveInterval: 3000, // Create new wave every 3 seconds
  // PacMan animation config
  pacmanSize: 35, // 35% of viewport size
  pacmanDuration: 8000, // 8 seconds for PacMan animation
};

// Available animation types
const ANIMATION_TYPES = {
  FALLING_COINS: 'falling_coins',
  PACMAN: 'pacman',
  BUGS_KING: 'bugs_king'
};

// Get easter egg hints
const hints = getEasterEggHints();

/**
 * Easter egg composable for Bitcoin logo rain animation
 * @returns {Object} Easter egg utilities and state
 */
export function useEasterEgg() {
  // Reactive state
  const isActive = ref(false);
  const animationsEnabled = ref(true); // Simplified for now - will be updated after downloading official logos
  const keySequence = ref([]);
  const animationElements = ref([]);

  // Media query for reduced motion
  let mediaQuery = null;
  let keyListener = null;
  let touchSequence = [];
  let touchListener = null;

  // Check if sequence matches the classic pattern
  const verifySequence = async (sequence) => {
    return await verifyClassicSequence(sequence);
  };

  // Create a single falling Bitcoin logo
  const createFallingLogo = () => {
    const logo = document.createElement("div");
    logo.className = "bitcoin-easter-egg-logo";

    // Random positioning and timing
    const startX =
      Math.random() * window.innerWidth * ANIMATION_CONFIG.horizontalSpread;
    const fallDuration =
      ANIMATION_CONFIG.fallSpeed.min +
      Math.random() *
        (ANIMATION_CONFIG.fallSpeed.max - ANIMATION_CONFIG.fallSpeed.min);
    const rotationSpeed =
      ANIMATION_CONFIG.rotationSpeed.min +
      Math.random() *
        (ANIMATION_CONFIG.rotationSpeed.max -
          ANIMATION_CONFIG.rotationSpeed.min);
    const delay = Math.random() * 1000; // Stagger the start times

    // Use the Bitcoin SVG directly
    const logoUrl = "/bitcoin-symbol.svg";

    // Set initial styles
    Object.assign(logo.style, {
      position: "fixed",
      left: `${startX}px`,
      top: "-50px",
      width: `${ANIMATION_CONFIG.logoSize}px`,
      height: `${ANIMATION_CONFIG.logoSize}px`,
      backgroundImage: `url(${logoUrl})`,
      backgroundSize: "contain",
      backgroundRepeat: "no-repeat",
      backgroundPosition: "center",
      zIndex: ANIMATION_CONFIG.zIndex,
      pointerEvents: "none",
      transform: "translate3d(0, 0, 0)", // Hardware acceleration
      willChange: "transform", // Optimize for animations
    });

    // Add to DOM
    document.body.appendChild(logo);
    animationElements.value.push(logo);

    // Animate the fall with rotation
    const startTime = performance.now() + delay;
    let _animationId;

    const animate = (currentTime) => {
      if (!isActive.value) {
        // Animation was cancelled
        if (logo.parentNode) {
          logo.parentNode.removeChild(logo);
        }
        return;
      }

      const elapsed = currentTime - startTime;
      if (elapsed < 0) {
        // Still waiting for delay
        _animationId = requestAnimationFrame(animate);
        return;
      }

      const progress = Math.min(elapsed / fallDuration, 1);

      // Easing function for realistic fall (gravity acceleration)
      const easeInQuad = progress * progress;
      const fallDistance = window.innerHeight + 100; // Fall past bottom of screen
      const currentY = easeInQuad * fallDistance;

      // Rotation
      const rotation = (elapsed / 1000) * rotationSpeed * 360;

      // Apply transform
      logo.style.transform = `translate3d(0, ${currentY}px, 0) rotate(${rotation}deg)`;

      if (progress < 1) {
        _animationId = requestAnimationFrame(animate);
      } else {
        // Animation complete, remove element
        if (logo.parentNode) {
          logo.parentNode.removeChild(logo);
        }
        // Remove from tracking array
        const index = animationElements.value.indexOf(logo);
        if (index > -1) {
          animationElements.value.splice(index, 1);
        }
      }
    };

    _animationId = requestAnimationFrame(animate);

    return logo;
  };

  // Create centered PacMan animation
  const createPacManAnimation = () => {
    const pacman = document.createElement("div");
    pacman.className = "bitcoin-easter-egg-pacman";

    // Calculate size (35% of viewport)
    const viewportSize = Math.min(window.innerWidth, window.innerHeight);
    const pacmanSize = viewportSize * (ANIMATION_CONFIG.pacmanSize / 100);

    // Center the PacMan
    const centerX = (window.innerWidth - pacmanSize) / 2;
    const centerY = (window.innerHeight - pacmanSize) / 2;

    // Set initial styles
    Object.assign(pacman.style, {
      position: "fixed",
      left: `${centerX}px`,
      top: `${centerY}px`,
      width: `${pacmanSize}px`,
      height: `${pacmanSize}px`,
      backgroundImage: `url(/BTC-PacMan-Fiat.gif)`,
      backgroundSize: "contain",
      backgroundRepeat: "no-repeat",
      backgroundPosition: "center",
      zIndex: ANIMATION_CONFIG.zIndex,
      pointerEvents: "none",
      opacity: "0",
      transform: "scale(0.5)",
      transition: "opacity 0.5s ease-in-out, transform 0.5s ease-in-out",
    });

    // Add to DOM and tracking
    document.body.appendChild(pacman);
    animationElements.value.push(pacman);

    // Animate in
    setTimeout(() => {
      pacman.style.opacity = "1";
      pacman.style.transform = "scale(1)";
    }, 100);

    // Animate out and cleanup
    setTimeout(() => {
      pacman.style.opacity = "0";
      pacman.style.transform = "scale(0.8)";
      
      setTimeout(() => {
        if (pacman.parentNode) {
          pacman.parentNode.removeChild(pacman);
        }
        // Remove from tracking array
        const index = animationElements.value.indexOf(pacman);
        if (index > -1) {
          animationElements.value.splice(index, 1);
        }
      }, 500);
    }, ANIMATION_CONFIG.pacmanDuration);

    return pacman;
  };

  // Create centered Bugs King animation
  const createBugsKingAnimation = () => {
    const bugsKing = document.createElement("div");
    bugsKing.className = "bitcoin-easter-egg-bugs-king";

    // Calculate size (35% of viewport)
    const viewportSize = Math.min(window.innerWidth, window.innerHeight);
    const bugsKingSize = viewportSize * (ANIMATION_CONFIG.pacmanSize / 100);

    // Center the Bugs King
    const centerX = (window.innerWidth - bugsKingSize) / 2;
    const centerY = (window.innerHeight - bugsKingSize) / 2;

    // Set initial styles
    Object.assign(bugsKing.style, {
      position: "fixed",
      left: `${centerX}px`,
      top: `${centerY}px`,
      width: `${bugsKingSize}px`,
      height: `${bugsKingSize}px`,
      backgroundImage: `url(/Bugs-King-BTC.gif)`,
      backgroundSize: "contain",
      backgroundRepeat: "no-repeat",
      backgroundPosition: "center",
      zIndex: ANIMATION_CONFIG.zIndex,
      pointerEvents: "none",
      opacity: "0",
      transform: "scale(0.5)",
      transition: "opacity 0.5s ease-in-out, transform 0.5s ease-in-out",
    });

    // Add to DOM and tracking
    document.body.appendChild(bugsKing);
    animationElements.value.push(bugsKing);

    // Animate in
    setTimeout(() => {
      bugsKing.style.opacity = "1";
      bugsKing.style.transform = "scale(1)";
    }, 100);

    // Animate out and cleanup
    setTimeout(() => {
      bugsKing.style.opacity = "0";
      bugsKing.style.transform = "scale(0.8)";
      
      setTimeout(() => {
        if (bugsKing.parentNode) {
          bugsKing.parentNode.removeChild(bugsKing);
        }
        // Remove from tracking array
        const index = animationElements.value.indexOf(bugsKing);
        if (index > -1) {
          animationElements.value.splice(index, 1);
        }
      }, 500);
    }, ANIMATION_CONFIG.pacmanDuration);

    return bugsKing;
  };

  // Randomly select and start an animation
  const startAnimation = () => {
    if (!animationsEnabled.value || isActive.value) return;

    console.log(hints.console);
    isActive.value = true;

    // Randomly choose animation type
    const animationTypes = Object.values(ANIMATION_TYPES);
    const randomType = animationTypes[Math.floor(Math.random() * animationTypes.length)];

    console.log(`🎮 Easter egg animation: ${randomType}`);

    if (randomType === ANIMATION_TYPES.PACMAN) {
      // PacMan animation
      createPacManAnimation();
      
      // Auto-cleanup after PacMan duration
      setTimeout(() => {
        stopAnimation();
      }, ANIMATION_CONFIG.pacmanDuration + 1000); // Extra time for fade out
      
    } else if (randomType === ANIMATION_TYPES.BUGS_KING) {
      // Bugs King animation
      createBugsKingAnimation();
      
      // Auto-cleanup after Bugs King duration
      setTimeout(() => {
        stopAnimation();
      }, ANIMATION_CONFIG.pacmanDuration + 1000); // Extra time for fade out
      
    } else {
      // Falling coins animation (default)
      const createWave = () => {
        if (!isActive.value) return;
        
        // Create a wave of logos with quick staggered timing
        for (let i = 0; i < ANIMATION_CONFIG.logoCount; i++) {
          setTimeout(() => {
            if (isActive.value) {
              createFallingLogo();
            }
          }, i * 100); // Quick stagger within each wave
        }
      };

      // Create first wave immediately
      createWave();

      // Create additional waves at intervals
      const waveCount = Math.floor(ANIMATION_CONFIG.duration / ANIMATION_CONFIG.waveInterval);
      for (let wave = 1; wave < waveCount; wave++) {
        setTimeout(() => {
          createWave();
        }, wave * ANIMATION_CONFIG.waveInterval);
      }

      // Auto-cleanup after animation duration
      setTimeout(() => {
        stopAnimation();
      }, ANIMATION_CONFIG.duration);
    }
  };

  // Stop the animation and cleanup
  const stopAnimation = () => {
    isActive.value = false;

    // Remove all animation elements
    animationElements.value.forEach((element) => {
      if (element.parentNode) {
        element.parentNode.removeChild(element);
      }
    });
    animationElements.value = [];
  };

  // Handle keyboard input
  const handleKeyDown = async (event) => {
    if (!animationsEnabled.value) return;

    // Add key to sequence
    keySequence.value.push(event.code);

    // Keep only the last CLASSIC_PATTERN_LENGTH keys
    if (keySequence.value.length > CLASSIC_PATTERN_LENGTH) {
      keySequence.value = keySequence.value.slice(-CLASSIC_PATTERN_LENGTH);
    }

    // Check if sequence matches
    if (keySequence.value.length === CLASSIC_PATTERN_LENGTH) {
      const isValid = await verifySequence(keySequence.value);
      if (isValid) {
        keySequence.value = []; // Reset sequence
        startAnimation();
      }
    }
  };

  // Handle touch sequence for mobile (tap on Bitcoin logo)
  const handleTouch = (event) => {
    if (!animationsEnabled.value) return;

    // Check if touch target is a Bitcoin logo
    const target = event.target;
    const isBitcoinLogo =
      target.closest(".bitcoin-logo") ||
      target.closest('[class*="bitcoin"]') ||
      (target.tagName === "svg" && target.innerHTML.includes("bitcoin"));

    if (isBitcoinLogo) {
      touchSequence.push(Date.now());

      // Keep only recent touches (within 3 seconds)
      const now = Date.now();
      touchSequence = touchSequence.filter((time) => now - time < 3000);

      // Check for rapid sequence (5 taps within 3 seconds)
      if (touchSequence.length >= 5) {
        touchSequence = [];
        startAnimation();
      }
    }
  };

  // Animation preference update function
  let updateAnimationPreference = null;

  // Setup accessibility monitoring
  const setupAccessibilityMonitoring = () => {
    if (typeof window !== "undefined" && window.matchMedia) {
      mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

      updateAnimationPreference = () => {
        animationsEnabled.value = !mediaQuery.matches;

        // Stop any active animation if animations are disabled
        if (mediaQuery.matches && isActive.value) {
          stopAnimation();
        }
      };

      updateAnimationPreference();

      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener("change", updateAnimationPreference);
      } else {
        mediaQuery.addListener(updateAnimationPreference);
      }
    }
  };

  // Computed properties
  const canActivate = computed(() => {
    return animationsEnabled.value && !isActive.value;
  });

  // Lifecycle hooks
  onMounted(() => {
    setupAccessibilityMonitoring();

    // Add keyboard listener
    keyListener = (event) => handleKeyDown(event);
    document.addEventListener("keydown", keyListener);

    // Add touch listener for mobile
    touchListener = (event) => handleTouch(event);
    document.addEventListener("touchend", touchListener);

    // Add subtle hint to console (only once per session)
    if (!window.bitcoinEasterEggHintShown) {
      console.log(`🎮 ${hints.footer} - ${hints.gaming}`);
      console.log(`💡 ${hints.code}`);
      console.log(`🕹️ ${hints.pattern}`);
      window.bitcoinEasterEggHintShown = true;
    }
  });

  onUnmounted(() => {
    // Cleanup
    stopAnimation();

    if (keyListener) {
      document.removeEventListener("keydown", keyListener);
    }

    if (touchListener) {
      document.removeEventListener("touchend", touchListener);
    }

    if (mediaQuery && updateAnimationPreference) {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", updateAnimationPreference);
      } else {
        mediaQuery.removeListener(updateAnimationPreference);
      }
    }
  });

  return {
    // Reactive state
    isActive,
    animationsEnabled,
    canActivate,

    // Methods
    startAnimation,
    stopAnimation,

    // For debugging (remove in production)
    _debugTrigger: () => {
      if (process.env.NODE_ENV === "development") {
        startAnimation();
      }
    },
  };
}

// Export the composable
export default useEasterEgg;
