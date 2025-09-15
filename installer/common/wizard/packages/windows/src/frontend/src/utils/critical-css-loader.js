/**
 * Critical CSS Loading System
 * Optimizes CSS loading for better performance
 */

/**
 * Critical CSS loader class
 */
export class CriticalCSSLoader {
  constructor() {
    this.criticalCSS = null;
    this.nonCriticalCSS = [];
    this.loadedCSS = new Set();
    this.init();
  }

  /**
   * Initialize critical CSS loading
   */
  init() {
    this.inlineCriticalCSS();
    this.loadNonCriticalCSS();
    this.optimizeWebFonts();
    this.preloadCriticalResources();
  }

  /**
   * Inline critical CSS for immediate rendering
   */
  inlineCriticalCSS() {
    // Check if critical CSS is already inlined
    if (document.querySelector("style[data-critical]")) {
      return;
    }

    const criticalCSS = `
      /* Critical CSS - Inlined for fast rendering */
      :root {
        --color-primary: #F7931A;
        --color-background: #121212;
        --color-surface: #1E1E1E;
        --color-text-primary: #FFFFFF;
        --color-text-secondary: #CCCCCC;
        --spacing-sm: 8px;
        --spacing-md: 16px;
        --spacing-lg: 24px;
        --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --font-size-body: 16px;
        --transition-fast: 0.15s ease;
        --radius-md: 8px;
      }
      
      * { box-sizing: border-box; }
      
      html {
        font-size: 16px;
        line-height: 1.6;
        color-scheme: dark;
      }
      
      body {
        margin: 0;
        padding: 0;
        font-family: var(--font-family);
        font-size: var(--font-size-body);
        color: var(--color-text-primary);
        background-color: var(--color-background);
        min-height: 100vh;
      }
      
      *:focus {
        outline: 2px solid var(--color-primary);
        outline-offset: 2px;
      }
      
      .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: var(--spacing-sm) var(--spacing-md);
        border: none;
        border-radius: var(--radius-md);
        font-size: var(--font-size-body);
        cursor: pointer;
        transition: all var(--transition-fast);
      }
      
      .btn-primary {
        background-color: var(--color-primary);
        color: #FFFFFF;
      }
      
      .spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 2px solid #333333;
        border-radius: 50%;
        border-top-color: var(--color-primary);
        animation: spin 1s ease-in-out infinite;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      .v-application {
        background-color: var(--color-background) !important;
      }
      
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: 0.01ms !important;
          transition-duration: 0.01ms !important;
        }
      }
    `;

    const style = document.createElement("style");
    style.setAttribute("data-critical", "true");
    style.textContent = criticalCSS;
    document.head.insertBefore(style, document.head.firstChild);
  }

  /**
   * Load non-critical CSS asynchronously
   */
  loadNonCriticalCSS() {
    // These CSS files are already imported in main.css, so no need to load them separately
    const nonCriticalFiles = [];

    // Use requestIdleCallback for better performance
    if ("requestIdleCallback" in window) {
      requestIdleCallback(() => {
        this.loadCSSFiles(nonCriticalFiles);
      });
    } else {
      // Fallback for browsers without requestIdleCallback
      setTimeout(() => {
        this.loadCSSFiles(nonCriticalFiles);
      }, 100);
    }
  }

  /**
   * Load CSS files asynchronously
   */
  loadCSSFiles(files) {
    files.forEach((file) => {
      if (!this.loadedCSS.has(file)) {
        this.loadCSS(file);
        this.loadedCSS.add(file);
      }
    });
  }

  /**
   * Load individual CSS file
   */
  loadCSS(href) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.media = "print"; // Load as print to avoid blocking
    link.onload = () => {
      link.media = "all"; // Switch to all media once loaded
    };

    // Add to head
    document.head.appendChild(link);

    // Fallback for older browsers
    setTimeout(() => {
      if (link.media === "print") {
        link.media = "all";
      }
    }, 3000);
  }

  /**
   * Optimize web font loading
   */
  optimizeWebFonts() {
    // Preload system fonts are already optimized
    // Add font-display: swap for any custom fonts
    const fontFaces = document.querySelectorAll(
      'style, link[rel="stylesheet"]',
    );

    fontFaces.forEach((element) => {
      if (element.textContent && element.textContent.includes("@font-face")) {
        // Add font-display: swap to existing font-face rules
        element.textContent = element.textContent.replace(
          /@font-face\s*{([^}]*)}/g,
          (match, content) => {
            if (!content.includes("font-display")) {
              return `@font-face { ${content} font-display: swap; }`;
            }
            return match;
          },
        );
      }
    });
  }

  /**
   * Preload critical resources
   */
  preloadCriticalResources() {
    const criticalResources = [
      // Bitcoin logo resources - preload for immediate availability
      { href: '/bitcoin-symbol.svg', as: 'image', type: 'image/svg+xml' },
      { href: '/bitcoin-symbol.png', as: 'image', type: 'image/png' },
      // CSS files are bundled in main.css, no need to preload separately
    ];

    criticalResources.forEach((resource) => {
      const link = document.createElement("link");
      link.rel = "preload";
      link.href = resource.href;
      link.as = resource.as;
      
      if (resource.type) {
        link.type = resource.type;
      }

      if (resource.as === "style") {
        link.onload = () => {
          const styleLink = document.createElement("link");
          styleLink.rel = "stylesheet";
          styleLink.href = resource.href;
          document.head.appendChild(styleLink);
        };
      }

      document.head.appendChild(link);
    });
    
    // Also call dedicated Bitcoin logo preloading
    this.preloadBitcoinLogos();
  }

  /**
   * Preload Bitcoin logos specifically for optimal performance
   */
  preloadBitcoinLogos() {
    const bitcoinLogos = [
      { 
        url: '/bitcoin-symbol.svg', 
        type: 'image/svg+xml',
        priority: 'high' // SVG used for smaller sizes (most common)
      },
      { 
        url: '/bitcoin-symbol.png', 
        type: 'image/png',
        priority: 'medium' // PNG used for larger sizes
      }
    ];

    bitcoinLogos.forEach((logo) => {
      // Use requestIdleCallback for non-blocking preload
      const preloadLogo = () => {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'image';
        link.href = logo.url;
        link.type = logo.type;
        
        // Add crossorigin for better caching
        link.crossOrigin = 'anonymous';
        
        // Add error handling
        link.onerror = () => {
          console.warn(`Failed to preload Bitcoin logo: ${logo.url}`);
        };
        
        link.onload = () => {
          console.log(`Bitcoin logo preloaded successfully: ${logo.url}`);
        };
        
        document.head.appendChild(link);
      };

      // Prioritize SVG (most commonly used) for immediate preload
      if (logo.priority === 'high') {
        preloadLogo();
      } else {
        // Delay PNG preload slightly to avoid blocking critical resources
        if ('requestIdleCallback' in window) {
          requestIdleCallback(preloadLogo, { timeout: 1000 });
        } else {
          setTimeout(preloadLogo, 100);
        }
      }
    });
  }

  /**
   * Monitor CSS loading performance
   */
  monitorPerformance() {
    if ("PerformanceObserver" in window) {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (entry.name.includes(".css")) {
            console.log(
              `CSS loaded: ${entry.name} in ${entry.duration.toFixed(2)}ms`,
            );
          }
        });
      });

      observer.observe({ entryTypes: ["resource"] });
    }
  }

  /**
   * Get CSS loading metrics
   */
  getMetrics() {
    const cssResources = performance
      .getEntriesByType("resource")
      .filter((entry) => entry.name.includes(".css"));

    const totalCSSTime = cssResources.reduce(
      (total, entry) => total + entry.duration,
      0,
    );
    const largestCSS = cssResources.reduce(
      (largest, entry) => (entry.duration > largest.duration ? entry : largest),
      { duration: 0 },
    );

    return {
      totalCSSFiles: cssResources.length,
      totalLoadTime: totalCSSTime,
      averageLoadTime: totalCSSTime / cssResources.length,
      largestCSS: largestCSS,
      loadedFiles: Array.from(this.loadedCSS),
    };
  }

  /**
   * Test Bitcoin logo preloading effectiveness
   */
  testBitcoinLogoPreloading() {
    const bitcoinLogos = ['/bitcoin-symbol.svg', '/bitcoin-symbol.png'];
    const results = {
      preloaded: [],
      failed: [],
      loadTimes: {}
    };

    bitcoinLogos.forEach(logoUrl => {
      const startTime = performance.now();
      
      // Check if resource was preloaded by looking at performance entries
      const resourceEntries = performance.getEntriesByName(logoUrl);
      
      if (resourceEntries.length > 0) {
        const entry = resourceEntries[0];
        results.preloaded.push(logoUrl);
        results.loadTimes[logoUrl] = {
          duration: entry.duration,
          transferSize: entry.transferSize,
          encodedBodySize: entry.encodedBodySize
        };
      } else {
        results.failed.push(logoUrl);
      }
    });

    // Test actual image loading to verify preloading effectiveness
    const testImageLoad = (url) => {
      return new Promise((resolve, reject) => {
        const img = new Image();
        const startTime = performance.now();
        
        img.onload = () => {
          const loadTime = performance.now() - startTime;
          resolve({ url, loadTime, cached: loadTime < 10 }); // < 10ms likely cached
        };
        
        img.onerror = () => {
          reject({ url, error: 'Failed to load' });
        };
        
        img.src = url;
      });
    };

    // Test loading performance
    Promise.all(bitcoinLogos.map(testImageLoad))
      .then(loadResults => {
        results.actualLoadTimes = loadResults;
        console.group('🪙 Bitcoin Logo Preloading Test Results');
        console.log('Preloaded resources:', results.preloaded);
        console.log('Failed preloads:', results.failed);
        console.log('Load performance:', results.actualLoadTimes);
        console.groupEnd();
      })
      .catch(error => {
        console.warn('Bitcoin logo preloading test failed:', error);
      });

    return results;
  }

  /**
   * Provide fallback behavior for failed preloads
   */
  handlePreloadFallback() {
    // Check if Bitcoin logos are available
    const checkLogoAvailability = async (url) => {
      try {
        const response = await fetch(url, { method: 'HEAD' });
        return response.ok;
      } catch (error) {
        console.warn(`Bitcoin logo not available: ${url}`, error);
        return false;
      }
    };

    // Fallback strategy for missing logos
    const provideFallback = (logoUrl) => {
      console.warn(`Providing fallback for missing Bitcoin logo: ${logoUrl}`);
      
      // Create a simple fallback using CSS
      const style = document.createElement('style');
      style.textContent = `
        .bitcoin-logo-fallback {
          display: inline-block;
          width: 32px;
          height: 32px;
          background: linear-gradient(45deg, #F7931A, #FFB84D);
          border-radius: 50%;
          position: relative;
        }
        .bitcoin-logo-fallback::before {
          content: '₿';
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          color: white;
          font-weight: bold;
          font-size: 18px;
        }
      `;
      document.head.appendChild(style);
    };

    // Test logo availability and provide fallbacks if needed
    ['/bitcoin-symbol.svg', '/bitcoin-symbol.png'].forEach(async (logoUrl) => {
      const isAvailable = await checkLogoAvailability(logoUrl);
      if (!isAvailable) {
        provideFallback(logoUrl);
      }
    });
  }
}

/**
 * CSS Bundle optimizer
 */
export class CSSBundleOptimizer {
  constructor() {
    this.unusedCSS = [];
    this.duplicateRules = [];
  }

  /**
   * Analyze CSS usage
   */
  analyzeCSSUsage() {
    const allStyleSheets = Array.from(document.styleSheets);
    const usedSelectors = new Set();
    const allSelectors = new Set();

    allStyleSheets.forEach((sheet) => {
      try {
        const rules = Array.from(sheet.cssRules || []);

        rules.forEach((rule) => {
          if (rule.selectorText) {
            allSelectors.add(rule.selectorText);

            // Check if selector is used in DOM
            try {
              if (document.querySelector(rule.selectorText)) {
                usedSelectors.add(rule.selectorText);
              }
            } catch (e) {
              // Invalid selector, skip
            }
          }
        });
      } catch (e) {
        // Cross-origin stylesheet, skip
      }
    });

    this.unusedCSS = Array.from(allSelectors).filter(
      (selector) => !usedSelectors.has(selector),
    );

    return {
      totalSelectors: allSelectors.size,
      usedSelectors: usedSelectors.size,
      unusedSelectors: this.unusedCSS.length,
      unusedCSS: this.unusedCSS,
    };
  }

  /**
   * Find duplicate CSS rules
   */
  findDuplicateRules() {
    const allStyleSheets = Array.from(document.styleSheets);
    const ruleMap = new Map();

    allStyleSheets.forEach((sheet) => {
      try {
        const rules = Array.from(sheet.cssRules || []);

        rules.forEach((rule) => {
          if (rule.selectorText && rule.style) {
            const key = `${rule.selectorText}:${rule.style.cssText}`;

            if (ruleMap.has(key)) {
              ruleMap.get(key).count++;
            } else {
              ruleMap.set(key, { rule: rule, count: 1 });
            }
          }
        });
      } catch (e) {
        // Cross-origin stylesheet, skip
      }
    });

    this.duplicateRules = Array.from(ruleMap.values())
      .filter((item) => item.count > 1)
      .map((item) => ({ selector: item.rule.selectorText, count: item.count }));

    return this.duplicateRules;
  }

  /**
   * Generate optimization report
   */
  generateOptimizationReport() {
    const usageAnalysis = this.analyzeCSSUsage();
    const duplicateAnalysis = this.findDuplicateRules();

    console.group("🎨 CSS Bundle Optimization Report");
    console.log(`📊 Total selectors: ${usageAnalysis.totalSelectors}`);
    console.log(`✅ Used selectors: ${usageAnalysis.usedSelectors}`);
    console.log(`❌ Unused selectors: ${usageAnalysis.unusedSelectors}`);
    console.log(`🔄 Duplicate rules: ${duplicateAnalysis.length}`);

    const optimizationPotential = Math.round(
      (usageAnalysis.unusedSelectors / usageAnalysis.totalSelectors) * 100,
    );
    console.log(`💡 Optimization potential: ${optimizationPotential}%`);

    if (usageAnalysis.unusedSelectors > 0) {
      console.group("❌ Unused Selectors (sample)");
      usageAnalysis.unusedCSS.slice(0, 10).forEach((selector) => {
        console.log(selector);
      });
      if (usageAnalysis.unusedCSS.length > 10) {
        console.log(`... and ${usageAnalysis.unusedCSS.length - 10} more`);
      }
      console.groupEnd();
    }

    if (duplicateAnalysis.length > 0) {
      console.group("🔄 Duplicate Rules");
      duplicateAnalysis.slice(0, 5).forEach((duplicate) => {
        console.log(`${duplicate.selector} (${duplicate.count} times)`);
      });
      console.groupEnd();
    }

    console.groupEnd();

    return {
      usage: usageAnalysis,
      duplicates: duplicateAnalysis,
      optimizationPotential: optimizationPotential,
    };
  }
}

/**
 * Initialize critical CSS loading system
 */
export function initializeCriticalCSSLoader() {
  const loader = new CriticalCSSLoader();
  const optimizer = new CSSBundleOptimizer();

  // Set up fallback handling for Bitcoin logos
  loader.handlePreloadFallback();

  // Add global optimization functions for development
  if (process.env.NODE_ENV === "development") {
    window.analyzeCSSUsage = () => optimizer.generateOptimizationReport();
    window.getCSSMetrics = () => loader.getMetrics();
    window.testBitcoinLogoPreloading = () => loader.testBitcoinLogoPreloading();
  }

  // Monitor performance
  loader.monitorPerformance();

  return { loader, optimizer };
}
