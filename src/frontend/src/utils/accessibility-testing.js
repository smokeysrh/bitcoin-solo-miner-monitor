/**
 * Accessibility Testing Utilities
 * Comprehensive testing suite for WCAG 2.1 AA compliance
 */

/**
 * Color contrast testing utility
 */
export class ContrastTester {
  constructor() {
    this.wcagAANormal = 4.5;
    this.wcagAALarge = 3.0;
    this.wcagAAANormal = 7.0;
    this.wcagAAALarge = 4.5;
  }

  /**
   * Calculate relative luminance of a color
   */
  getLuminance(r, g, b) {
    const [rs, gs, bs] = [r, g, b].map((c) => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  /**
   * Calculate contrast ratio between two colors
   */
  getContrastRatio(color1, color2) {
    const lum1 = this.getLuminance(...this.hexToRgb(color1));
    const lum2 = this.getLuminance(...this.hexToRgb(color2));
    const brightest = Math.max(lum1, lum2);
    const darkest = Math.min(lum1, lum2);
    return (brightest + 0.05) / (darkest + 0.05);
  }

  /**
   * Convert hex color to RGB
   */
  hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? [
          parseInt(result[1], 16),
          parseInt(result[2], 16),
          parseInt(result[3], 16),
        ]
      : null;
  }

  /**
   * Test if contrast ratio meets WCAG standards
   */
  testContrast(foreground, background, isLargeText = false) {
    const ratio = this.getContrastRatio(foreground, background);

    return {
      ratio: ratio,
      passAA: ratio >= (isLargeText ? this.wcagAALarge : this.wcagAANormal),
      passAAA: ratio >= (isLargeText ? this.wcagAAALarge : this.wcagAAANormal),
      level: this.getComplianceLevel(ratio, isLargeText),
    };
  }

  /**
   * Get compliance level for contrast ratio
   */
  getComplianceLevel(ratio, isLargeText) {
    const aaThreshold = isLargeText ? this.wcagAALarge : this.wcagAANormal;
    const aaaThreshold = isLargeText ? this.wcagAAALarge : this.wcagAAANormal;

    if (ratio >= aaaThreshold) return "AAA";
    if (ratio >= aaThreshold) return "AA";
    return "FAIL";
  }

  /**
   * Test all color combinations in the application
   */
  testAllColorCombinations() {
    const colorCombinations = [
      // Primary combinations
      {
        name: "Primary on Dark Background",
        fg: "#F7931A",
        bg: "#121212",
        large: false,
      },
      {
        name: "Primary on Surface",
        fg: "#F7931A",
        bg: "#1E1E1E",
        large: false,
      },
      {
        name: "Primary Text on Primary",
        fg: "#121212",
        bg: "#F7931A",
        large: false,
      },

      // Text combinations
      {
        name: "Primary Text on Dark",
        fg: "#FFFFFF",
        bg: "#121212",
        large: false,
      },
      {
        name: "Primary Text on Surface",
        fg: "#FFFFFF",
        bg: "#1E1E1E",
        large: false,
      },
      {
        name: "Secondary Text on Dark",
        fg: "#CCCCCC",
        bg: "#121212",
        large: false,
      },
      {
        name: "Secondary Text on Surface",
        fg: "#CCCCCC",
        bg: "#1E1E1E",
        large: false,
      },
      {
        name: "Disabled Text on Dark",
        fg: "#999999",
        bg: "#121212",
        large: false,
      },
      {
        name: "Disabled Text on Surface",
        fg: "#999999",
        bg: "#1E1E1E",
        large: false,
      },

      // Status combinations
      { name: "Success on Dark", fg: "#4CAF50", bg: "#121212", large: false },
      { name: "Warning on Dark", fg: "#FFB74D", bg: "#121212", large: false },
      { name: "Error on Dark", fg: "#FF6B6B", bg: "#121212", large: false },
      { name: "Info on Dark", fg: "#64B5F6", bg: "#121212", large: false },

      // Link combinations
      { name: "Link Default", fg: "#64B5F6", bg: "#121212", large: false },
      { name: "Link Hover", fg: "#90CAF9", bg: "#121212", large: false },
      { name: "Link Visited", fg: "#CE93D8", bg: "#121212", large: false },

      // Large text combinations
      {
        name: "Primary on Dark (Large)",
        fg: "#F7931A",
        bg: "#121212",
        large: true,
      },
      {
        name: "Secondary Text on Dark (Large)",
        fg: "#CCCCCC",
        bg: "#121212",
        large: true,
      },
      {
        name: "Disabled Text on Surface (Large)",
        fg: "#999999",
        bg: "#1E1E1E",
        large: true,
      },
    ];

    const results = colorCombinations.map((combo) => {
      const test = this.testContrast(combo.fg, combo.bg, combo.large);
      return {
        name: combo.name,
        foreground: combo.fg,
        background: combo.bg,
        isLargeText: combo.large,
        ...test,
      };
    });

    return results;
  }

  /**
   * Generate contrast test report
   */
  generateReport() {
    const results = this.testAllColorCombinations();
    const passed = results.filter((r) => r.passAA);
    const failed = results.filter((r) => !r.passAA);

    console.group("🎨 Color Contrast Test Report");
    console.log(`✅ Passed: ${passed.length}/${results.length} combinations`);
    console.log(`❌ Failed: ${failed.length}/${results.length} combinations`);

    if (failed.length > 0) {
      console.group("❌ Failed Combinations");
      failed.forEach((result) => {
        console.log(
          `${result.name}: ${result.ratio.toFixed(2)}:1 (${result.level})`,
        );
      });
      console.groupEnd();
    }

    console.group("✅ Passed Combinations");
    passed.forEach((result) => {
      console.log(
        `${result.name}: ${result.ratio.toFixed(2)}:1 (${result.level})`,
      );
    });
    console.groupEnd();

    console.groupEnd();

    return {
      total: results.length,
      passed: passed.length,
      failed: failed.length,
      results: results,
    };
  }
}

/**
 * Focus management testing utility
 */
export class FocusTester {
  constructor() {
    this.focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ];
  }

  /**
   * Test if all interactive elements are focusable
   */
  testFocusableElements() {
    const allInteractive = document.querySelectorAll(
      this.focusableSelectors.join(", "),
    );
    const results = [];

    allInteractive.forEach((element, index) => {
      const isFocusable = this.isElementFocusable(element);
      const hasVisibleFocus = this.hasVisibleFocusIndicator(element);

      results.push({
        element: element,
        tagName: element.tagName.toLowerCase(),
        id: element.id || `element-${index}`,
        className: element.className,
        isFocusable: isFocusable,
        hasVisibleFocus: hasVisibleFocus,
        tabIndex: element.tabIndex,
        ariaLabel: element.getAttribute("aria-label"),
        ariaLabelledBy: element.getAttribute("aria-labelledby"),
      });
    });

    return results;
  }

  /**
   * Check if element is actually focusable
   */
  isElementFocusable(element) {
    return (
      element.offsetWidth > 0 &&
      element.offsetHeight > 0 &&
      !element.hidden &&
      !element.disabled &&
      element.tabIndex !== -1
    );
  }

  /**
   * Check if element has visible focus indicator
   */
  hasVisibleFocusIndicator(element) {
    // Temporarily focus the element to test focus styles
    const originalFocus = document.activeElement;
    element.focus();

    const computedStyle = window.getComputedStyle(element);
    const hasOutline =
      computedStyle.outline !== "none" &&
      computedStyle.outline !== "0px" &&
      computedStyle.outline !== "";
    const hasBoxShadow = computedStyle.boxShadow !== "none";
    const hasBorder = computedStyle.border !== "none";

    // Restore original focus
    if (originalFocus) {
      originalFocus.focus();
    } else {
      element.blur();
    }

    return hasOutline || hasBoxShadow || hasBorder;
  }

  /**
   * Test tab order and keyboard navigation
   */
  testTabOrder() {
    const focusableElements = Array.from(
      document.querySelectorAll(this.focusableSelectors.join(", ")),
    )
      .filter((el) => this.isElementFocusable(el))
      .sort((a, b) => {
        const aIndex = a.tabIndex || 0;
        const bIndex = b.tabIndex || 0;

        if (aIndex === bIndex) {
          // Use DOM order for elements with same tabIndex
          return (
            Array.from(document.querySelectorAll("*")).indexOf(a) -
            Array.from(document.querySelectorAll("*")).indexOf(b)
          );
        }

        return aIndex - bIndex;
      });

    const tabOrderIssues = [];

    focusableElements.forEach((element, index) => {
      const expectedTabIndex = index + 1;
      const actualTabIndex = element.tabIndex || 0;

      if (actualTabIndex > 0 && actualTabIndex !== expectedTabIndex) {
        tabOrderIssues.push({
          element: element,
          expected: expectedTabIndex,
          actual: actualTabIndex,
          issue: "Unexpected tab index",
        });
      }
    });

    return {
      focusableElements: focusableElements,
      tabOrderIssues: tabOrderIssues,
      totalFocusable: focusableElements.length,
    };
  }

  /**
   * Generate focus test report
   */
  generateReport() {
    const focusableResults = this.testFocusableElements();
    const tabOrderResults = this.testTabOrder();

    const focusableCount = focusableResults.length;
    const withVisibleFocus = focusableResults.filter(
      (r) => r.hasVisibleFocus,
    ).length;
    const withoutVisibleFocus = focusableResults.filter(
      (r) => !r.hasVisibleFocus,
    );

    console.group("⌨️ Focus Management Test Report");
    console.log(`🎯 Total focusable elements: ${focusableCount}`);
    console.log(`✅ With visible focus: ${withVisibleFocus}/${focusableCount}`);
    console.log(
      `❌ Without visible focus: ${withoutVisibleFocus.length}/${focusableCount}`,
    );
    console.log(
      `📋 Tab order issues: ${tabOrderResults.tabOrderIssues.length}`,
    );

    if (withoutVisibleFocus.length > 0) {
      console.group("❌ Elements without visible focus");
      withoutVisibleFocus.forEach((result) => {
        console.log(
          `${result.tagName}${result.id ? "#" + result.id : ""}${result.className ? "." + result.className.split(" ")[0] : ""}`,
        );
      });
      console.groupEnd();
    }

    if (tabOrderResults.tabOrderIssues.length > 0) {
      console.group("📋 Tab Order Issues");
      tabOrderResults.tabOrderIssues.forEach((issue) => {
        console.log(
          `${issue.element.tagName}: Expected ${issue.expected}, Got ${issue.actual}`,
        );
      });
      console.groupEnd();
    }

    console.groupEnd();

    return {
      focusableElements: focusableResults,
      tabOrder: tabOrderResults,
      summary: {
        totalFocusable: focusableCount,
        withVisibleFocus: withVisibleFocus,
        withoutVisibleFocus: withoutVisibleFocus.length,
        tabOrderIssues: tabOrderResults.tabOrderIssues.length,
      },
    };
  }
}

/**
 * ARIA and semantic testing utility
 */
export class ARIATester {
  constructor() {
    this.requiredARIAElements = [
      {
        selector: '[role="button"]',
        requiredAttrs: ["aria-label", "aria-labelledby"],
      },
      {
        selector: '[role="dialog"]',
        requiredAttrs: ["aria-labelledby", "aria-modal"],
      },
      {
        selector: '[role="navigation"]',
        requiredAttrs: ["aria-label", "aria-labelledby"],
      },
      { selector: '[role="main"]', requiredAttrs: [] },
      {
        selector: 'input[type="checkbox"]',
        requiredAttrs: ["aria-label", "aria-labelledby"],
      },
      {
        selector: 'input[type="radio"]',
        requiredAttrs: ["aria-label", "aria-labelledby"],
      },
    ];
  }

  /**
   * Test ARIA attributes and roles
   */
  testARIACompliance() {
    const results = [];

    this.requiredARIAElements.forEach((rule) => {
      const elements = document.querySelectorAll(rule.selector);

      elements.forEach((element) => {
        const hasRequiredAttrs =
          rule.requiredAttrs.length === 0 ||
          rule.requiredAttrs.some((attr) => element.hasAttribute(attr));

        results.push({
          element: element,
          selector: rule.selector,
          requiredAttrs: rule.requiredAttrs,
          hasRequiredAttrs: hasRequiredAttrs,
          presentAttrs: rule.requiredAttrs.filter((attr) =>
            element.hasAttribute(attr),
          ),
          missingAttrs: rule.requiredAttrs.filter(
            (attr) => !element.hasAttribute(attr),
          ),
        });
      });
    });

    return results;
  }

  /**
   * Test semantic HTML structure
   */
  testSemanticStructure() {
    const semanticElements = {
      main: document.querySelectorAll("main"),
      nav: document.querySelectorAll("nav"),
      header: document.querySelectorAll("header"),
      footer: document.querySelectorAll("footer"),
      section: document.querySelectorAll("section"),
      article: document.querySelectorAll("article"),
      aside: document.querySelectorAll("aside"),
      h1: document.querySelectorAll("h1"),
      h2: document.querySelectorAll("h2"),
      h3: document.querySelectorAll("h3"),
      h4: document.querySelectorAll("h4"),
      h5: document.querySelectorAll("h5"),
      h6: document.querySelectorAll("h6"),
    };

    const issues = [];

    // Check for single main element
    if (semanticElements.main.length === 0) {
      issues.push("Missing main element");
    } else if (semanticElements.main.length > 1) {
      issues.push("Multiple main elements found");
    }

    // Check heading hierarchy
    const headings = Array.from(
      document.querySelectorAll("h1, h2, h3, h4, h5, h6"),
    ).map((h) => ({ element: h, level: parseInt(h.tagName.charAt(1)) }));

    for (let i = 1; i < headings.length; i++) {
      const current = headings[i];
      const previous = headings[i - 1];

      if (current.level > previous.level + 1) {
        issues.push(
          `Heading hierarchy skip: ${previous.element.tagName} to ${current.element.tagName}`,
        );
      }
    }

    return {
      semanticElements: Object.keys(semanticElements).map((tag) => ({
        tag: tag,
        count: semanticElements[tag].length,
      })),
      issues: issues,
      headingHierarchy: headings,
    };
  }

  /**
   * Generate ARIA test report
   */
  generateReport() {
    const ariaResults = this.testARIACompliance();
    const semanticResults = this.testSemanticStructure();

    const ariaIssues = ariaResults.filter((r) => !r.hasRequiredAttrs);

    console.group("🏷️ ARIA and Semantic Test Report");
    console.log(`🎯 ARIA elements tested: ${ariaResults.length}`);
    console.log(`❌ ARIA issues: ${ariaIssues.length}`);
    console.log(`🏗️ Semantic issues: ${semanticResults.issues.length}`);

    if (ariaIssues.length > 0) {
      console.group("❌ ARIA Issues");
      ariaIssues.forEach((issue) => {
        console.log(
          `${issue.selector}: Missing ${issue.missingAttrs.join(", ")}`,
        );
      });
      console.groupEnd();
    }

    if (semanticResults.issues.length > 0) {
      console.group("🏗️ Semantic Issues");
      semanticResults.issues.forEach((issue) => {
        console.log(issue);
      });
      console.groupEnd();
    }

    console.group("📊 Semantic Elements Count");
    semanticResults.semanticElements.forEach((element) => {
      console.log(`${element.tag}: ${element.count}`);
    });
    console.groupEnd();

    console.groupEnd();

    return {
      aria: ariaResults,
      semantic: semanticResults,
      summary: {
        ariaIssues: ariaIssues.length,
        semanticIssues: semanticResults.issues.length,
        totalTested: ariaResults.length,
      },
    };
  }
}

/**
 * Performance testing for accessibility features
 */
export class AccessibilityPerformanceTester {
  constructor() {
    this.metrics = {};
  }

  /**
   * Test CSS performance impact
   */
  testCSSPerformance() {
    const startTime = performance.now();

    // Force style recalculation
    document.body.offsetHeight;

    const endTime = performance.now();
    const styleRecalcTime = endTime - startTime;

    // Test animation performance
    const animationStartTime = performance.now();
    const testElement = document.createElement("div");
    testElement.style.cssText = `
      position: absolute;
      top: -1000px;
      left: -1000px;
      width: 100px;
      height: 100px;
      background: var(--color-primary);
      transition: transform 0.3s ease;
    `;
    document.body.appendChild(testElement);

    testElement.style.transform = "translateX(100px)";

    setTimeout(() => {
      const animationEndTime = performance.now();
      const animationTime = animationEndTime - animationStartTime;
      document.body.removeChild(testElement);

      this.metrics.cssPerformance = {
        styleRecalcTime: styleRecalcTime,
        animationTime: animationTime,
      };
    }, 350);

    return this.metrics.cssPerformance;
  }

  /**
   * Test focus management performance
   */
  testFocusPerformance() {
    const focusableElements = document.querySelectorAll(
      "button, input, a, [tabindex]",
    );
    const startTime = performance.now();

    // Test focus cycling performance
    let currentIndex = 0;
    const focusCycle = () => {
      if (currentIndex < Math.min(focusableElements.length, 10)) {
        focusableElements[currentIndex].focus();
        currentIndex++;
        requestAnimationFrame(focusCycle);
      } else {
        const endTime = performance.now();
        this.metrics.focusPerformance = {
          totalTime: endTime - startTime,
          elementsPerSecond: (currentIndex / (endTime - startTime)) * 1000,
        };
      }
    };

    focusCycle();

    return this.metrics.focusPerformance;
  }

  /**
   * Generate performance report
   */
  generateReport() {
    console.group("⚡ Accessibility Performance Report");

    if (this.metrics.cssPerformance) {
      console.log(
        `🎨 Style recalc time: ${this.metrics.cssPerformance.styleRecalcTime.toFixed(2)}ms`,
      );
      console.log(
        `🎬 Animation time: ${this.metrics.cssPerformance.animationTime.toFixed(2)}ms`,
      );
    }

    if (this.metrics.focusPerformance) {
      console.log(
        `⌨️ Focus cycle time: ${this.metrics.focusPerformance.totalTime.toFixed(2)}ms`,
      );
      console.log(
        `🎯 Focus elements/sec: ${this.metrics.focusPerformance.elementsPerSecond.toFixed(2)}`,
      );
    }

    console.groupEnd();

    return this.metrics;
  }
}

/**
 * Comprehensive accessibility test runner
 */
export class AccessibilityTestRunner {
  constructor() {
    this.contrastTester = new ContrastTester();
    this.focusTester = new FocusTester();
    this.ariaTester = new ARIATester();
    this.performanceTester = new AccessibilityPerformanceTester();
  }

  /**
   * Run all accessibility tests
   */
  async runAllTests() {
    console.log("🚀 Starting comprehensive accessibility test suite...");

    const results = {
      contrast: this.contrastTester.generateReport(),
      focus: this.focusTester.generateReport(),
      aria: this.ariaTester.generateReport(),
      performance: this.performanceTester.generateReport(),
    };

    // Calculate overall score
    const totalTests =
      results.contrast.total +
      results.focus.summary.totalFocusable +
      results.aria.summary.totalTested;

    const passedTests =
      results.contrast.passed +
      results.focus.summary.withVisibleFocus +
      (results.aria.summary.totalTested - results.aria.summary.ariaIssues);

    const overallScore = Math.round((passedTests / totalTests) * 100);

    console.group("📊 Overall Accessibility Score");
    console.log(`🎯 Score: ${overallScore}%`);
    console.log(`✅ Passed: ${passedTests}/${totalTests} tests`);
    console.log(`❌ Failed: ${totalTests - passedTests}/${totalTests} tests`);
    console.groupEnd();

    return {
      ...results,
      overall: {
        score: overallScore,
        passed: passedTests,
        total: totalTests,
        failed: totalTests - passedTests,
      },
    };
  }

  /**
   * Run tests and save results to localStorage
   */
  async runAndSaveTests() {
    const results = await this.runAllTests();

    // Save results to localStorage for debugging
    localStorage.setItem(
      "accessibility-test-results",
      JSON.stringify(results, null, 2),
    );

    return results;
  }
}

/**
 * Initialize accessibility testing
 */
export function initializeAccessibilityTesting() {
  const testRunner = new AccessibilityTestRunner();

  // Add global testing functions
  window.testAccessibility = () => testRunner.runAllTests();
  window.testContrast = () => testRunner.contrastTester.generateReport();
  window.testFocus = () => testRunner.focusTester.generateReport();
  window.testARIA = () => testRunner.ariaTester.generateReport();

  // Run tests in development mode
  if (process.env.NODE_ENV === "development") {
    console.log(
      "🧪 Accessibility testing utilities loaded. Use window.testAccessibility() to run tests.",
    );
  }

  return testRunner;
}
