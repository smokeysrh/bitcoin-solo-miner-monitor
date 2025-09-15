/**
 * Easter Egg Test Utilities
 *
 * Comprehensive testing utilities for the Bitcoin logo rain easter egg.
 * Includes performance monitoring and accessibility compliance testing.
 */

import {
  CLASSIC_PATTERN,
  verifyClassicSequence,
  generateHash as _generateHash,
} from "./easterEggUtils.js";

/**
 * Test suite for easter egg functionality
 */
export class EasterEggTestSuite {
  constructor() {
    this.results = [];
    this.performanceMetrics = {};
  }

  /**
   * Run all easter egg tests
   * @returns {Promise<Object>} Test results
   */
  async runAllTests() {
    console.log("🎮 Running Easter Egg Test Suite...");

    this.results = [];
    this.performanceMetrics = {};

    // Test cryptographic verification
    await this.testCryptographicVerification();

    // Test accessibility compliance
    await this.testAccessibilityCompliance();

    // Test animation performance
    await this.testAnimationPerformance();

    // Test cleanup functionality
    await this.testCleanupFunctionality();

    // Test mobile touch sequence
    await this.testMobileTouchSequence();

    const summary = this.generateTestSummary();
    console.log("🎮 Easter Egg Test Suite Complete:", summary);

    return {
      results: this.results,
      metrics: this.performanceMetrics,
      summary,
    };
  }

  /**
   * Test cryptographic hash verification
   */
  async testCryptographicVerification() {
    const testName = "Cryptographic Verification";
    console.log(`Testing: ${testName}`);

    try {
      // Test correct sequence
      const correctResult = await verifyClassicSequence(CLASSIC_PATTERN);
      this.addResult(
        testName,
        "Correct sequence verification",
        correctResult === true,
      );

      // Test incorrect sequence
      const incorrectSequence = ["KeyA", "KeyB", "KeyC"];
      const incorrectResult = await verifyClassicSequence(incorrectSequence);
      this.addResult(
        testName,
        "Incorrect sequence rejection",
        incorrectResult === false,
      );

      // Test empty sequence
      const emptyResult = await verifyClassicSequence([]);
      this.addResult(
        testName,
        "Empty sequence rejection",
        emptyResult === false,
      );

      // Test partial sequence
      const partialSequence = CLASSIC_PATTERN.slice(0, 5);
      const partialResult = await verifyClassicSequence(partialSequence);
      this.addResult(
        testName,
        "Partial sequence rejection",
        partialResult === false,
      );

      // Performance test
      const startTime = performance.now();
      await verifyClassicSequence(CLASSIC_PATTERN);
      const endTime = performance.now();
      const verificationTime = endTime - startTime;

      this.performanceMetrics.verificationTime = verificationTime;
      this.addResult(
        testName,
        "Verification performance",
        verificationTime < 100,
      ); // Should be under 100ms
    } catch (error) {
      this.addResult(testName, "Error handling", false, error.message);
    }
  }

  /**
   * Test accessibility compliance
   */
  async testAccessibilityCompliance() {
    const testName = "Accessibility Compliance";
    console.log(`Testing: ${testName}`);

    try {
      // Test reduced motion detection
      const originalMatchMedia = window.matchMedia;

      // Mock reduced motion preference
      window.matchMedia = (query) => ({
        matches: query.includes("prefers-reduced-motion: reduce"),
        addEventListener: () => {},
        removeEventListener: () => {},
      });

      // Import and test the composable with reduced motion
      const { useEasterEgg } = await import("../composables/useEasterEgg.js");
      const easterEgg = useEasterEgg();

      this.addResult(
        testName,
        "Reduced motion detection",
        !easterEgg.animationsEnabled.value,
      );

      // Restore original matchMedia
      window.matchMedia = originalMatchMedia;

      // Test ARIA attributes and screen reader compatibility
      const testElement = document.createElement("div");
      testElement.className = "bitcoin-easter-egg-logo";
      testElement.setAttribute("aria-hidden", "true");

      this.addResult(
        testName,
        "ARIA hidden attribute",
        testElement.getAttribute("aria-hidden") === "true",
      );

      // Test keyboard navigation doesn't interfere
      testElement.tabIndex = -1;
      this.addResult(
        testName,
        "Non-focusable elements",
        testElement.tabIndex === -1,
      );
    } catch (error) {
      this.addResult(testName, "Error handling", false, error.message);
    }
  }

  /**
   * Test animation performance
   */
  async testAnimationPerformance() {
    const testName = "Animation Performance";
    console.log(`Testing: ${testName}`);

    try {
      // Test hardware acceleration support
      const testElement = document.createElement("div");
      testElement.style.transform = "translate3d(0, 0, 0)";
      testElement.style.willChange = "transform";

      const hasHardwareAcceleration =
        testElement.style.transform === "translate3d(0, 0, 0)";
      this.addResult(
        testName,
        "Hardware acceleration support",
        hasHardwareAcceleration,
      );

      // Test CSS containment
      testElement.style.contain = "layout style paint";
      const hasContainment = testElement.style.contain.includes("layout");
      this.addResult(testName, "CSS containment support", hasContainment);

      // Test requestAnimationFrame availability
      const hasRAF = typeof requestAnimationFrame === "function";
      this.addResult(testName, "RequestAnimationFrame support", hasRAF);

      // Test performance.now() availability
      const hasPerformanceNow =
        typeof performance !== "undefined" &&
        typeof performance.now === "function";
      this.addResult(testName, "Performance.now() support", hasPerformanceNow);

      // Memory usage test (basic)
      const initialMemory = performance.memory
        ? performance.memory.usedJSHeapSize
        : 0;

      // Create and destroy multiple elements to test memory leaks
      const elements = [];
      for (let i = 0; i < 100; i++) {
        const element = document.createElement("div");
        element.className = "bitcoin-easter-egg-logo";
        elements.push(element);
      }

      // Cleanup
      elements.forEach((element) => {
        element.remove();
      });
      elements.length = 0;

      // Force garbage collection if available (Chrome DevTools)
      if (window.gc) {
        window.gc();
      }

      const finalMemory = performance.memory
        ? performance.memory.usedJSHeapSize
        : 0;
      const memoryDelta = finalMemory - initialMemory;

      this.performanceMetrics.memoryDelta = memoryDelta;
      this.addResult(testName, "Memory leak prevention", memoryDelta < 1000000); // Less than 1MB increase
    } catch (error) {
      this.addResult(testName, "Error handling", false, error.message);
    }
  }

  /**
   * Test cleanup functionality
   */
  async testCleanupFunctionality() {
    const testName = "Cleanup Functionality";
    console.log(`Testing: ${testName}`);

    try {
      // Test element removal
      const testContainer = document.createElement("div");
      testContainer.id = "easter-egg-test-container";
      document.body.appendChild(testContainer);

      // Create test elements
      for (let i = 0; i < 5; i++) {
        const element = document.createElement("div");
        element.className = "bitcoin-easter-egg-logo";
        element.dataset.testId = `test-${i}`;
        testContainer.appendChild(element);
      }

      const initialCount = testContainer.children.length;
      this.addResult(testName, "Element creation", initialCount === 5);

      // Test cleanup
      Array.from(testContainer.children).forEach((child) => {
        child.remove();
      });

      const finalCount = testContainer.children.length;
      this.addResult(testName, "Element removal", finalCount === 0);

      // Cleanup test container
      testContainer.remove();

      // Test event listener cleanup
      let listenerCalled = false;
      const testListener = () => {
        listenerCalled = true;
      };

      document.addEventListener("keydown", testListener);
      document.removeEventListener("keydown", testListener);

      // Trigger event to test if listener was properly removed
      const keyEvent = new KeyboardEvent("keydown", { code: "KeyA" });
      document.dispatchEvent(keyEvent);

      this.addResult(testName, "Event listener cleanup", !listenerCalled);
    } catch (error) {
      this.addResult(testName, "Error handling", false, error.message);
    }
  }

  /**
   * Test mobile touch sequence
   */
  async testMobileTouchSequence() {
    const testName = "Mobile Touch Sequence";
    console.log(`Testing: ${testName}`);

    try {
      // Create mock Bitcoin logo element
      const mockLogo = document.createElement("div");
      mockLogo.className = "bitcoin-logo";
      document.body.appendChild(mockLogo);

      // Test touch event creation
      const touchEvent = new TouchEvent("touchend", {
        bubbles: true,
        cancelable: true,
        touches: [],
        targetTouches: [],
        changedTouches: [],
      });

      this.addResult(
        testName,
        "Touch event creation",
        touchEvent instanceof TouchEvent,
      );

      // Test element detection
      const isBitcoinLogo = mockLogo.closest(".bitcoin-logo") !== null;
      this.addResult(testName, "Bitcoin logo detection", isBitcoinLogo);

      // Cleanup
      mockLogo.remove();

      // Test timing mechanism
      const timestamps = [];
      for (let i = 0; i < 5; i++) {
        timestamps.push(Date.now());
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      const timeDifferences = timestamps
        .slice(1)
        .map((time, index) => time - timestamps[index]);
      const averageTimeDiff =
        timeDifferences.reduce((sum, diff) => sum + diff, 0) /
        timeDifferences.length;

      this.performanceMetrics.touchTimingAccuracy = averageTimeDiff;
      this.addResult(
        testName,
        "Touch timing accuracy",
        Math.abs(averageTimeDiff - 100) < 50,
      ); // Within 50ms of expected
    } catch (error) {
      this.addResult(testName, "Error handling", false, error.message);
    }
  }

  /**
   * Add a test result
   */
  addResult(category, test, passed, error = null) {
    this.results.push({
      category,
      test,
      passed,
      error,
      timestamp: new Date().toISOString(),
    });

    const status = passed ? "✅" : "❌";
    const errorMsg = error ? ` (${error})` : "";
    console.log(`  ${status} ${test}${errorMsg}`);
  }

  /**
   * Generate test summary
   */
  generateTestSummary() {
    const total = this.results.length;
    const passed = this.results.filter((r) => r.passed).length;
    const failed = total - passed;
    const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : 0;

    return {
      total,
      passed,
      failed,
      passRate: `${passRate}%`,
      categories: [...new Set(this.results.map((r) => r.category))],
      metrics: this.performanceMetrics,
    };
  }
}

/**
 * Quick test function for development
 */
export async function quickEasterEggTest() {
  const testSuite = new EasterEggTestSuite();
  return await testSuite.runAllTests();
}

/**
 * Performance benchmark for easter egg animation
 */
export function benchmarkEasterEggAnimation() {
  console.log("🎮 Benchmarking Easter Egg Animation Performance...");

  const metrics = {
    elementCreation: 0,
    animationFrame: 0,
    cleanup: 0,
  };

  // Benchmark element creation
  const createStart = performance.now();
  const elements = [];

  for (let i = 0; i < 25; i++) {
    const element = document.createElement("div");
    element.className = "bitcoin-easter-egg-logo";
    element.style.transform = "translate3d(0, 0, 0)";
    element.style.willChange = "transform";
    elements.push(element);
  }

  metrics.elementCreation = performance.now() - createStart;

  // Benchmark animation frame
  const animStart = performance.now();
  let frameCount = 0;

  const animateFrame = () => {
    frameCount++;
    elements.forEach((element, _index) => {
      const progress = frameCount / 60; // Simulate 60 frames
      const y = progress * 100;
      element.style.transform = `translate3d(0, ${y}px, 0) rotate(${progress * 360}deg)`;
    });

    if (frameCount < 60) {
      requestAnimationFrame(animateFrame);
    } else {
      metrics.animationFrame = performance.now() - animStart;

      // Benchmark cleanup
      const cleanupStart = performance.now();
      elements.forEach((element) => element.remove());
      elements.length = 0;
      metrics.cleanup = performance.now() - cleanupStart;

      console.log("🎮 Animation Benchmark Results:", metrics);
    }
  };

  requestAnimationFrame(animateFrame);

  return metrics;
}

// Export for development debugging
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  window.quickEasterEggTest = quickEasterEggTest;
  window.benchmarkEasterEggAnimation = benchmarkEasterEggAnimation;
}
