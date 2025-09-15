/**
 * WCAG 2.1 AA Compliance Validator
 * Comprehensive validation for Web Content Accessibility Guidelines
 */

/**
 * WCAG Color Contrast Validator
 */
export class WCAGContrastValidator {
  constructor() {
    this.wcagLevels = {
      AA: { normal: 4.5, large: 3.0 },
      AAA: { normal: 7.0, large: 4.5 },
    };
  }

  /**
   * Validate all color combinations in the application
   */
  validateAllContrasts() {
    const colorTests = [
      // Primary Bitcoin Orange combinations
      {
        name: "Bitcoin Orange on Dark Background",
        fg: "#F7931A",
        bg: "#121212",
        context: "Primary buttons, links",
      },
      {
        name: "Bitcoin Orange on Surface",
        fg: "#F7931A",
        bg: "#1E1E1E",
        context: "Cards, panels",
      },
      {
        name: "Dark text on Bitcoin Orange",
        fg: "#121212",
        bg: "#F7931A",
        context: "Button text",
      },

      // Text combinations
      {
        name: "Primary text on dark",
        fg: "#FFFFFF",
        bg: "#121212",
        context: "Main content text",
      },
      {
        name: "Primary text on surface",
        fg: "#FFFFFF",
        bg: "#1E1E1E",
        context: "Card content",
      },
      {
        name: "Secondary text on dark",
        fg: "#CCCCCC",
        bg: "#121212",
        context: "Secondary content",
      },
      {
        name: "Secondary text on surface",
        fg: "#CCCCCC",
        bg: "#1E1E1E",
        context: "Card secondary text",
      },
      {
        name: "Disabled text on dark",
        fg: "#999999",
        bg: "#121212",
        context: "Disabled elements",
      },
      {
        name: "Disabled text on surface",
        fg: "#999999",
        bg: "#1E1E1E",
        context: "Disabled form fields",
      },

      // Status colors
      {
        name: "Success green on dark",
        fg: "#4CAF50",
        bg: "#121212",
        context: "Success messages",
      },
      {
        name: "Warning orange on dark",
        fg: "#FFB74D",
        bg: "#121212",
        context: "Warning messages",
      },
      {
        name: "Error red on dark",
        fg: "#FF6B6B",
        bg: "#121212",
        context: "Error messages",
      },
      {
        name: "Info blue on dark",
        fg: "#64B5F6",
        bg: "#121212",
        context: "Info messages",
      },

      // Interactive elements
      {
        name: "Link default",
        fg: "#64B5F6",
        bg: "#121212",
        context: "Default links",
      },
      {
        name: "Link hover",
        fg: "#90CAF9",
        bg: "#121212",
        context: "Hovered links",
      },
      {
        name: "Link visited",
        fg: "#CE93D8",
        bg: "#121212",
        context: "Visited links",
      },

      // Form elements
      {
        name: "Input text",
        fg: "#FFFFFF",
        bg: "#2A2A2A",
        context: "Form inputs",
      },
      {
        name: "Placeholder text",
        fg: "#999999",
        bg: "#2A2A2A",
        context: "Input placeholders",
      },
      {
        name: "Border on surface",
        fg: "#555555",
        bg: "#1E1E1E",
        context: "Element borders",
      },
    ];

    const results = colorTests.map((test) => {
      const contrast = this.calculateContrast(test.fg, test.bg);
      const passAA = contrast >= this.wcagLevels.AA.normal;
      const passAALarge = contrast >= this.wcagLevels.AA.large;
      const passAAA = contrast >= this.wcagLevels.AAA.normal;

      return {
        ...test,
        contrast: contrast,
        passAA: passAA,
        passAALarge: passAALarge,
        passAAA: passAAA,
        recommendation: this.getRecommendation(contrast, test.context),
      };
    });

    return results;
  }

  /**
   * Calculate contrast ratio between two colors
   */
  calculateContrast(color1, color2) {
    const lum1 = this.getLuminance(color1);
    const lum2 = this.getLuminance(color2);
    const brightest = Math.max(lum1, lum2);
    const darkest = Math.min(lum1, lum2);
    return (brightest + 0.05) / (darkest + 0.05);
  }

  /**
   * Get relative luminance of a color
   */
  getLuminance(color) {
    const rgb = this.hexToRgb(color);
    if (!rgb) return 0;

    const [r, g, b] = rgb.map((c) => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });

    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  /**
   * Convert hex to RGB
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
   * Get recommendation for improving contrast
   */
  getRecommendation(contrast, _context) {
    if (contrast >= this.wcagLevels.AAA.normal) {
      return "Excellent contrast - exceeds AAA standards";
    } else if (contrast >= this.wcagLevels.AA.normal) {
      return "Good contrast - meets AA standards";
    } else if (contrast >= this.wcagLevels.AA.large) {
      return "Acceptable for large text only - consider darker/lighter variant for normal text";
    } else {
      return "Insufficient contrast - requires color adjustment";
    }
  }

  /**
   * Generate detailed contrast report
   */
  generateContrastReport() {
    const results = this.validateAllContrasts();
    const passed = results.filter((r) => r.passAA);
    const failed = results.filter((r) => !r.passAA);
    const excellent = results.filter((r) => r.passAAA);

    console.group("🎨 WCAG 2.1 AA Contrast Validation Report");
    console.log(
      `✅ Passed AA: ${passed.length}/${results.length} (${Math.round((passed.length / results.length) * 100)}%)`,
    );
    console.log(
      `⭐ Exceeded AAA: ${excellent.length}/${results.length} (${Math.round((excellent.length / results.length) * 100)}%)`,
    );
    console.log(
      `❌ Failed AA: ${failed.length}/${results.length} (${Math.round((failed.length / results.length) * 100)}%)`,
    );

    if (failed.length > 0) {
      console.group("❌ Failed Combinations");
      failed.forEach((result) => {
        console.log(
          `${result.name}: ${result.contrast.toFixed(2)}:1 - ${result.recommendation}`,
        );
      });
      console.groupEnd();
    }

    console.group("✅ Passed Combinations");
    passed.forEach((result) => {
      const level = result.passAAA ? "AAA" : "AA";
      console.log(
        `${result.name}: ${result.contrast.toFixed(2)}:1 (${level}) - ${result.context}`,
      );
    });
    console.groupEnd();

    console.groupEnd();

    return {
      total: results.length,
      passed: passed.length,
      failed: failed.length,
      excellent: excellent.length,
      results: results,
      score: Math.round((passed.length / results.length) * 100),
    };
  }
}

/**
 * WCAG Keyboard Navigation Validator
 */
export class WCAGKeyboardValidator {
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
   * Validate keyboard accessibility
   */
  validateKeyboardAccess() {
    const results = {
      focusableElements: this.validateFocusableElements(),
      tabOrder: this.validateTabOrder(),
      skipLinks: this.validateSkipLinks(),
      focusIndicators: this.validateFocusIndicators(),
      keyboardTraps: this.validateKeyboardTraps(),
    };

    return results;
  }

  /**
   * Validate focusable elements
   */
  validateFocusableElements() {
    const elements = document.querySelectorAll(
      this.focusableSelectors.join(", "),
    );
    const issues = [];

    elements.forEach((element, _index) => {
      // Check if element is actually focusable
      const isVisible =
        element.offsetWidth > 0 && element.offsetHeight > 0 && !element.hidden;
      const _hasTabIndex = element.hasAttribute("tabindex");
      const tabIndexValue = element.getAttribute("tabindex");

      if (!isVisible && tabIndexValue !== "-1") {
        issues.push({
          element: element,
          issue: "Hidden element is focusable",
          severity: "high",
        });
      }

      // Check for missing labels
      if (
        ["input", "textarea", "select"].includes(element.tagName.toLowerCase())
      ) {
        const hasLabel = element.labels && element.labels.length > 0;
        const hasAriaLabel = element.hasAttribute("aria-label");
        const hasAriaLabelledBy = element.hasAttribute("aria-labelledby");

        if (!hasLabel && !hasAriaLabel && !hasAriaLabelledBy) {
          issues.push({
            element: element,
            issue: "Form element missing accessible label",
            severity: "high",
          });
        }
      }

      // Check for custom interactive elements
      if (
        element.hasAttribute("onclick") &&
        !this.focusableSelectors.some((sel) => element.matches(sel))
      ) {
        issues.push({
          element: element,
          issue: "Interactive element not keyboard accessible",
          severity: "high",
        });
      }
    });

    return {
      totalElements: elements.length,
      issues: issues,
      score: Math.max(
        0,
        Math.round((1 - issues.length / elements.length) * 100),
      ),
    };
  }

  /**
   * Validate tab order
   */
  validateTabOrder() {
    const focusableElements = Array.from(
      document.querySelectorAll(this.focusableSelectors.join(", ")),
    ).filter((el) => el.offsetWidth > 0 && el.offsetHeight > 0 && !el.hidden);

    const issues = [];
    const _previousTabIndex = 0;

    focusableElements.forEach((element, index) => {
      const tabIndex = parseInt(element.getAttribute("tabindex")) || 0;

      // Check for positive tab indices (generally not recommended)
      if (tabIndex > 0) {
        issues.push({
          element: element,
          issue: `Positive tabindex (${tabIndex}) disrupts natural tab order`,
          severity: "medium",
        });
      }

      // Check for logical tab order
      const rect = element.getBoundingClientRect();
      if (index > 0) {
        const prevElement = focusableElements[index - 1];
        const prevRect = prevElement.getBoundingClientRect();

        // Check if tab order follows visual order (top to bottom, left to right)
        if (rect.top < prevRect.top - 10 && rect.left < prevRect.left - 10) {
          issues.push({
            element: element,
            issue: "Tab order may not follow visual order",
            severity: "low",
          });
        }
      }
    });

    return {
      totalElements: focusableElements.length,
      issues: issues,
      score: Math.max(
        0,
        Math.round((1 - issues.length / focusableElements.length) * 100),
      ),
    };
  }

  /**
   * Validate skip links
   */
  validateSkipLinks() {
    const skipLinks = document.querySelectorAll(
      'a[href^="#"]:first-child, .skip-link, .skip-nav',
    );
    const issues = [];

    if (skipLinks.length === 0) {
      issues.push({
        issue: "No skip links found - keyboard users cannot skip navigation",
        severity: "high",
      });
    } else {
      skipLinks.forEach((link) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target) {
          issues.push({
            element: link,
            issue: "Skip link target does not exist",
            severity: "high",
          });
        }

        // Check if skip link is visually hidden but becomes visible on focus
        const computedStyle = window.getComputedStyle(link);
        const isHidden =
          computedStyle.position === "absolute" &&
          (computedStyle.left.includes("-") || computedStyle.top.includes("-"));

        if (!isHidden) {
          // Skip link should be hidden by default
          issues.push({
            element: link,
            issue: "Skip link should be visually hidden until focused",
            severity: "low",
          });
        }
      });
    }

    return {
      skipLinksFound: skipLinks.length,
      issues: issues,
      score: skipLinks.length > 0 && issues.length === 0 ? 100 : 0,
    };
  }

  /**
   * Validate focus indicators
   */
  validateFocusIndicators() {
    const focusableElements = document.querySelectorAll(
      this.focusableSelectors.join(", "),
    );
    const issues = [];

    focusableElements.forEach((element) => {
      // Temporarily focus element to check focus styles
      const originalFocus = document.activeElement;
      element.focus();

      const computedStyle = window.getComputedStyle(element);
      const hasOutline =
        computedStyle.outline !== "none" && computedStyle.outline !== "0px";
      const hasBoxShadow = computedStyle.boxShadow !== "none";
      const hasBorderChange = computedStyle.borderColor !== "initial";

      if (!hasOutline && !hasBoxShadow && !hasBorderChange) {
        issues.push({
          element: element,
          issue: "No visible focus indicator",
          severity: "high",
        });
      }

      // Restore original focus
      if (originalFocus) {
        originalFocus.focus();
      } else {
        element.blur();
      }
    });

    return {
      totalElements: focusableElements.length,
      issues: issues,
      score: Math.max(
        0,
        Math.round((1 - issues.length / focusableElements.length) * 100),
      ),
    };
  }

  /**
   * Validate keyboard traps
   */
  validateKeyboardTraps() {
    const modals = document.querySelectorAll(
      '[role="dialog"], .modal, .v-dialog',
    );
    const issues = [];

    modals.forEach((modal) => {
      const isVisible = modal.offsetWidth > 0 && modal.offsetHeight > 0;
      if (isVisible) {
        const focusableInModal = modal.querySelectorAll(
          this.focusableSelectors.join(", "),
        );

        if (focusableInModal.length === 0) {
          issues.push({
            element: modal,
            issue: "Modal has no focusable elements",
            severity: "high",
          });
        }

        // Check for close button
        const closeButton = modal.querySelector(
          '[aria-label*="close" i], .close, .modal-close',
        );
        if (!closeButton) {
          issues.push({
            element: modal,
            issue: "Modal missing accessible close button",
            severity: "medium",
          });
        }
      }
    });

    return {
      modalsFound: modals.length,
      issues: issues,
      score: issues.length === 0 ? 100 : Math.max(0, 100 - issues.length * 25),
    };
  }

  /**
   * Generate keyboard accessibility report
   */
  generateKeyboardReport() {
    const results = this.validateKeyboardAccess();

    const totalIssues = Object.values(results).reduce(
      (sum, category) => sum + (category.issues ? category.issues.length : 0),
      0,
    );

    const averageScore =
      Object.values(results).reduce(
        (sum, category) => sum + (category.score || 0),
        0,
      ) / Object.keys(results).length;

    console.group("⌨️ WCAG 2.1 AA Keyboard Accessibility Report");
    console.log(`📊 Overall Score: ${Math.round(averageScore)}%`);
    console.log(`🎯 Total Issues: ${totalIssues}`);

    Object.entries(results).forEach(([category, data]) => {
      const categoryName = category
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (str) => str.toUpperCase());
      console.log(
        `${categoryName}: ${data.score || 0}% (${data.issues ? data.issues.length : 0} issues)`,
      );
    });

    // Show high severity issues
    const highSeverityIssues = Object.values(results)
      .flatMap((category) => category.issues || [])
      .filter((issue) => issue.severity === "high");

    if (highSeverityIssues.length > 0) {
      console.group("🚨 High Severity Issues");
      highSeverityIssues.forEach((issue) => {
        console.log(
          `${issue.issue}${issue.element ? ` (${issue.element.tagName})` : ""}`,
        );
      });
      console.groupEnd();
    }

    console.groupEnd();

    return {
      ...results,
      summary: {
        overallScore: Math.round(averageScore),
        totalIssues: totalIssues,
        highSeverityIssues: highSeverityIssues.length,
      },
    };
  }
}

/**
 * WCAG Semantic Structure Validator
 */
export class WCAGSemanticValidator {
  constructor() {
    this.requiredLandmarks = ["main", "navigation", "banner", "contentinfo"];
    this.headingLevels = ["h1", "h2", "h3", "h4", "h5", "h6"];
  }

  /**
   * Validate semantic structure
   */
  validateSemanticStructure() {
    return {
      landmarks: this.validateLandmarks(),
      headings: this.validateHeadings(),
      lists: this.validateLists(),
      tables: this.validateTables(),
      forms: this.validateForms(),
      images: this.validateImages(),
    };
  }

  /**
   * Validate landmark regions
   */
  validateLandmarks() {
    const landmarks = {
      main: document.querySelectorAll('main, [role="main"]'),
      navigation: document.querySelectorAll('nav, [role="navigation"]'),
      banner: document.querySelectorAll('header, [role="banner"]'),
      contentinfo: document.querySelectorAll('footer, [role="contentinfo"]'),
    };

    const issues = [];

    // Check for required landmarks
    if (landmarks.main.length === 0) {
      issues.push({ issue: "Missing main landmark", severity: "high" });
    } else if (landmarks.main.length > 1) {
      issues.push({
        issue: "Multiple main landmarks found",
        severity: "medium",
      });
    }

    if (landmarks.navigation.length === 0) {
      issues.push({ issue: "Missing navigation landmark", severity: "medium" });
    }

    // Check for proper labeling of multiple landmarks
    Object.entries(landmarks).forEach(([type, elements]) => {
      if (elements.length > 1) {
        elements.forEach((element) => {
          const hasLabel =
            element.hasAttribute("aria-label") ||
            element.hasAttribute("aria-labelledby");
          if (!hasLabel) {
            issues.push({
              element: element,
              issue: `Multiple ${type} landmarks should have unique labels`,
              severity: "medium",
            });
          }
        });
      }
    });

    return {
      landmarks: Object.fromEntries(
        Object.entries(landmarks).map(([key, value]) => [key, value.length]),
      ),
      issues: issues,
      score: Math.max(0, 100 - issues.length * 20),
    };
  }

  /**
   * Validate heading structure
   */
  validateHeadings() {
    const headings = Array.from(
      document.querySelectorAll(this.headingLevels.join(", ")),
    ).map((h) => ({
      element: h,
      level: parseInt(h.tagName.charAt(1)),
      text: h.textContent.trim(),
    }));

    const issues = [];

    // Check for h1
    const h1Count = headings.filter((h) => h.level === 1).length;
    if (h1Count === 0) {
      issues.push({ issue: "Missing h1 heading", severity: "high" });
    } else if (h1Count > 1) {
      issues.push({ issue: "Multiple h1 headings found", severity: "medium" });
    }

    // Check heading hierarchy
    for (let i = 1; i < headings.length; i++) {
      const current = headings[i];
      const previous = headings[i - 1];

      if (current.level > previous.level + 1) {
        issues.push({
          element: current.element,
          issue: `Heading level skip: ${previous.level} to ${current.level}`,
          severity: "medium",
        });
      }
    }

    // Check for empty headings
    headings.forEach((heading) => {
      if (!heading.text) {
        issues.push({
          element: heading.element,
          issue: "Empty heading",
          severity: "high",
        });
      }
    });

    return {
      totalHeadings: headings.length,
      headingLevels: this.headingLevels.map((level) => ({
        level: level,
        count: headings.filter((h) => h.level === parseInt(level.charAt(1)))
          .length,
      })),
      issues: issues,
      score: Math.max(0, 100 - issues.length * 15),
    };
  }

  /**
   * Validate lists
   */
  validateLists() {
    const lists = document.querySelectorAll("ul, ol, dl");
    const issues = [];

    lists.forEach((list) => {
      const listItems = list.querySelectorAll("li, dt, dd");

      if (listItems.length === 0) {
        issues.push({
          element: list,
          issue: "Empty list",
          severity: "medium",
        });
      }

      // Check for proper nesting
      if (list.tagName === "DL") {
        const terms = list.querySelectorAll("dt");
        const _descriptions = list.querySelectorAll("dd");

        if (terms.length === 0) {
          issues.push({
            element: list,
            issue: "Description list missing terms",
            severity: "high",
          });
        }
      }
    });

    return {
      totalLists: lists.length,
      issues: issues,
      score: Math.max(0, 100 - issues.length * 20),
    };
  }

  /**
   * Validate tables
   */
  validateTables() {
    const tables = document.querySelectorAll("table");
    const issues = [];

    tables.forEach((table) => {
      // Check for table headers
      const headers = table.querySelectorAll("th");
      const caption = table.querySelector("caption");

      if (headers.length === 0) {
        issues.push({
          element: table,
          issue: "Table missing headers",
          severity: "high",
        });
      }

      // Check for table caption or summary
      if (
        !caption &&
        !table.hasAttribute("aria-label") &&
        !table.hasAttribute("aria-labelledby")
      ) {
        issues.push({
          element: table,
          issue: "Table missing caption or accessible name",
          severity: "medium",
        });
      }

      // Check for complex table structure
      const hasRowHeaders =
        table.querySelectorAll('th[scope="row"]').length > 0;
      const hasColHeaders =
        table.querySelectorAll('th[scope="col"]').length > 0;

      if (headers.length > 0 && !hasRowHeaders && !hasColHeaders) {
        issues.push({
          element: table,
          issue: "Table headers missing scope attributes",
          severity: "medium",
        });
      }
    });

    return {
      totalTables: tables.length,
      issues: issues,
      score: Math.max(0, 100 - issues.length * 25),
    };
  }

  /**
   * Validate forms
   */
  validateForms() {
    const forms = document.querySelectorAll("form");
    const formControls = document.querySelectorAll("input, textarea, select");
    const issues = [];

    formControls.forEach((control) => {
      // Check for labels
      const hasLabel = control.labels && control.labels.length > 0;
      const hasAriaLabel = control.hasAttribute("aria-label");
      const hasAriaLabelledBy = control.hasAttribute("aria-labelledby");

      if (!hasLabel && !hasAriaLabel && !hasAriaLabelledBy) {
        issues.push({
          element: control,
          issue: "Form control missing label",
          severity: "high",
        });
      }

      // Check for required field indicators
      if (control.hasAttribute("required")) {
        const hasRequiredIndicator =
          control.hasAttribute("aria-required") ||
          (control.labels &&
            Array.from(control.labels).some(
              (label) =>
                label.textContent.includes("*") ||
                label.textContent.toLowerCase().includes("required"),
            ));

        if (!hasRequiredIndicator) {
          issues.push({
            element: control,
            issue: "Required field missing indicator",
            severity: "medium",
          });
        }
      }
    });

    return {
      totalForms: forms.length,
      totalControls: formControls.length,
      issues: issues,
      score: Math.max(0, 100 - issues.length * 10),
    };
  }

  /**
   * Validate images
   */
  validateImages() {
    const images = document.querySelectorAll("img");
    const issues = [];

    images.forEach((img) => {
      const hasAlt = img.hasAttribute("alt");
      const altText = img.getAttribute("alt");

      if (!hasAlt) {
        issues.push({
          element: img,
          issue: "Image missing alt attribute",
          severity: "high",
        });
      } else if (
        (altText && altText.toLowerCase().includes("image")) ||
        altText.toLowerCase().includes("picture")
      ) {
        issues.push({
          element: img,
          issue: "Alt text contains redundant words (image, picture)",
          severity: "low",
        });
      }

      // Check for decorative images
      if (
        img.hasAttribute("role") &&
        img.getAttribute("role") === "presentation"
      ) {
        if (altText && altText.trim() !== "") {
          issues.push({
            element: img,
            issue: "Decorative image should have empty alt text",
            severity: "medium",
          });
        }
      }
    });

    return {
      totalImages: images.length,
      issues: issues,
      score: Math.max(0, 100 - issues.length * 15),
    };
  }

  /**
   * Generate semantic structure report
   */
  generateSemanticReport() {
    const results = this.validateSemanticStructure();

    const totalIssues = Object.values(results).reduce(
      (sum, category) => sum + (category.issues ? category.issues.length : 0),
      0,
    );

    const averageScore =
      Object.values(results).reduce(
        (sum, category) => sum + (category.score || 0),
        0,
      ) / Object.keys(results).length;

    console.group("🏗️ WCAG 2.1 AA Semantic Structure Report");
    console.log(`📊 Overall Score: ${Math.round(averageScore)}%`);
    console.log(`🎯 Total Issues: ${totalIssues}`);

    Object.entries(results).forEach(([category, data]) => {
      const categoryName = category
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (str) => str.toUpperCase());
      console.log(
        `${categoryName}: ${data.score || 0}% (${data.issues ? data.issues.length : 0} issues)`,
      );
    });

    console.groupEnd();

    return {
      ...results,
      summary: {
        overallScore: Math.round(averageScore),
        totalIssues: totalIssues,
      },
    };
  }
}

/**
 * Comprehensive WCAG 2.1 AA Validator
 */
export class WCAGValidator {
  constructor() {
    this.contrastValidator = new WCAGContrastValidator();
    this.keyboardValidator = new WCAGKeyboardValidator();
    this.semanticValidator = new WCAGSemanticValidator();
  }

  /**
   * Run complete WCAG 2.1 AA validation
   */
  async validateComplete() {
    console.log("🚀 Starting comprehensive WCAG 2.1 AA validation...");

    const results = {
      contrast: this.contrastValidator.generateContrastReport(),
      keyboard: this.keyboardValidator.generateKeyboardReport(),
      semantic: this.semanticValidator.generateSemanticReport(),
      timestamp: new Date().toISOString(),
    };

    // Calculate overall compliance score
    const scores = [
      results.contrast.score,
      results.keyboard.summary.overallScore,
      results.semantic.summary.overallScore,
    ];

    const overallScore = Math.round(
      scores.reduce((sum, score) => sum + score, 0) / scores.length,
    );

    console.group("🏆 WCAG 2.1 AA Compliance Summary");
    console.log(`📊 Overall Compliance: ${overallScore}%`);
    console.log(`🎨 Color Contrast: ${results.contrast.score}%`);
    console.log(
      `⌨️ Keyboard Access: ${results.keyboard.summary.overallScore}%`,
    );
    console.log(
      `🏗️ Semantic Structure: ${results.semantic.summary.overallScore}%`,
    );

    const complianceLevel =
      overallScore >= 90
        ? "Excellent"
        : overallScore >= 80
          ? "Good"
          : overallScore >= 70
            ? "Needs Improvement"
            : "Poor";

    console.log(`🎯 Compliance Level: ${complianceLevel}`);
    console.groupEnd();

    // Save results for debugging
    localStorage.setItem(
      "wcag-validation-results",
      JSON.stringify(results, null, 2),
    );

    return {
      ...results,
      overall: {
        score: overallScore,
        level: complianceLevel,
        recommendations: this.getRecommendations(results),
      },
    };
  }

  /**
   * Get recommendations based on validation results
   */
  getRecommendations(results) {
    const recommendations = [];

    if (results.contrast.score < 90) {
      recommendations.push(
        "Improve color contrast ratios for better readability",
      );
    }

    if (results.keyboard.summary.overallScore < 90) {
      recommendations.push("Enhance keyboard navigation and focus management");
    }

    if (results.semantic.summary.overallScore < 90) {
      recommendations.push("Improve semantic HTML structure and ARIA usage");
    }

    if (results.keyboard.summary.highSeverityIssues > 0) {
      recommendations.push(
        "Address high severity keyboard accessibility issues immediately",
      );
    }

    return recommendations;
  }
}

/**
 * Initialize WCAG validation
 */
export function initializeWCAGValidation() {
  const validator = new WCAGValidator();

  // Add global validation functions
  window.validateWCAG = () => validator.validateComplete();
  window.validateContrast = () =>
    validator.contrastValidator.generateContrastReport();
  window.validateKeyboard = () =>
    validator.keyboardValidator.generateKeyboardReport();
  window.validateSemantic = () =>
    validator.semanticValidator.generateSemanticReport();

  console.log(
    "🧪 WCAG 2.1 AA validation utilities loaded. Use window.validateWCAG() to run complete validation.",
  );

  return validator;
}
