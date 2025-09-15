/**
 * Focus Management Utilities
 * Comprehensive focus management for accessibility compliance
 */

/**
 * Focus trap implementation for modals and dialogs
 */
export class FocusTrap {
  constructor(element) {
    this.element = element;
    this.focusableElements = [];
    this.firstFocusableElement = null;
    this.lastFocusableElement = null;
    this.previouslyFocusedElement = null;
    this.isActive = false;

    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.updateFocusableElements();
  }

  /**
   * Get all focusable elements within the trap
   */
  updateFocusableElements() {
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(", ");

    this.focusableElements = Array.from(
      this.element.querySelectorAll(focusableSelectors),
    ).filter((el) => {
      return el.offsetWidth > 0 && el.offsetHeight > 0 && !el.hidden;
    });

    this.firstFocusableElement = this.focusableElements[0];
    this.lastFocusableElement =
      this.focusableElements[this.focusableElements.length - 1];
  }

  /**
   * Activate the focus trap
   */
  activate() {
    if (this.isActive) return;

    this.previouslyFocusedElement = document.activeElement;
    this.updateFocusableElements();

    if (this.firstFocusableElement) {
      this.firstFocusableElement.focus();
    }

    document.addEventListener("keydown", this.handleKeyDown);
    this.isActive = true;
  }

  /**
   * Deactivate the focus trap
   */
  deactivate() {
    if (!this.isActive) return;

    document.removeEventListener("keydown", this.handleKeyDown);

    if (this.previouslyFocusedElement) {
      this.previouslyFocusedElement.focus();
    }

    this.isActive = false;
  }

  /**
   * Handle keydown events for focus trapping
   */
  handleKeyDown(event) {
    if (event.key !== "Tab") return;

    if (this.focusableElements.length === 0) {
      event.preventDefault();
      return;
    }

    if (event.shiftKey) {
      // Shift + Tab
      if (document.activeElement === this.firstFocusableElement) {
        event.preventDefault();
        this.lastFocusableElement.focus();
      }
    } else {
      // Tab
      if (document.activeElement === this.lastFocusableElement) {
        event.preventDefault();
        this.firstFocusableElement.focus();
      }
    }
  }
}

/**
 * Focus management for skip links
 */
export class SkipLinkManager {
  constructor() {
    this.skipLinks = [];
    this.init();
  }

  init() {
    // Create skip links container
    const skipLinksContainer = document.createElement("div");
    skipLinksContainer.className = "skip-links";
    skipLinksContainer.setAttribute("role", "navigation");
    skipLinksContainer.setAttribute("aria-label", "Skip navigation links");

    // Add skip links
    const skipLinks = [
      { href: "#main-content", text: "Skip to main content" },
      { href: "#navigation", text: "Skip to navigation" },
      { href: "#footer", text: "Skip to footer" },
    ];

    skipLinks.forEach((link) => {
      const skipLink = document.createElement("a");
      skipLink.href = link.href;
      skipLink.textContent = link.text;
      skipLink.className = "skip-link";
      skipLinksContainer.appendChild(skipLink);
      this.skipLinks.push(skipLink);
    });

    // Insert at the beginning of the body
    document.body.insertBefore(skipLinksContainer, document.body.firstChild);
  }
}

/**
 * Keyboard navigation manager
 */
export class KeyboardNavigationManager {
  constructor() {
    this.currentFocusIndex = -1;
    this.focusableElements = [];
    this.init();
  }

  init() {
    document.addEventListener("keydown", this.handleGlobalKeyDown.bind(this));
    this.updateFocusableElements();

    // Update focusable elements when DOM changes
    const observer = new MutationObserver(() => {
      this.updateFocusableElements();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["disabled", "hidden", "tabindex"],
    });
  }

  updateFocusableElements() {
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(", ");

    this.focusableElements = Array.from(
      document.querySelectorAll(focusableSelectors),
    ).filter((el) => {
      return el.offsetWidth > 0 && el.offsetHeight > 0 && !el.hidden;
    });
  }

  handleGlobalKeyDown(event) {
    // Handle global keyboard shortcuts
    if (event.altKey && event.key === "k") {
      // Alt+K: Focus search
      event.preventDefault();
      this.focusSearch();
    } else if (event.altKey && event.key === "m") {
      // Alt+M: Focus main navigation
      event.preventDefault();
      this.focusMainNavigation();
    } else if (event.altKey && event.key === "c") {
      // Alt+C: Focus main content
      event.preventDefault();
      this.focusMainContent();
    }
  }

  focusSearch() {
    const searchInput = document.querySelector(
      'input[type="search"], input[placeholder*="search" i]',
    );
    if (searchInput) {
      searchInput.focus();
      this.announceToScreenReader("Search focused");
    }
  }

  focusMainNavigation() {
    const mainNav = document.querySelector(
      'nav[role="navigation"], .main-navigation, #navigation',
    );
    if (mainNav) {
      const firstLink = mainNav.querySelector("a, button");
      if (firstLink) {
        firstLink.focus();
        this.announceToScreenReader("Main navigation focused");
      }
    }
  }

  focusMainContent() {
    const mainContent = document.querySelector(
      'main, #main-content, [role="main"]',
    );
    if (mainContent) {
      mainContent.focus();
      this.announceToScreenReader("Main content focused");
    }
  }

  announceToScreenReader(message) {
    const announcement = document.createElement("div");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }
}

/**
 * Modal focus management
 */
export class ModalFocusManager {
  constructor() {
    this.activeModals = [];
    this.init();
  }

  init() {
    document.addEventListener("keydown", this.handleEscapeKey.bind(this));
  }

  openModal(modalElement) {
    const focusTrap = new FocusTrap(modalElement);

    const modalData = {
      element: modalElement,
      focusTrap: focusTrap,
    };

    this.activeModals.push(modalData);
    focusTrap.activate();

    // Set ARIA attributes
    modalElement.setAttribute("role", "dialog");
    modalElement.setAttribute("aria-modal", "true");

    // Find and set aria-labelledby if there's a title
    const title = modalElement.querySelector(".modal-title, h1, h2, h3");
    if (title) {
      if (!title.id) {
        title.id = `modal-title-${Date.now()}`;
      }
      modalElement.setAttribute("aria-labelledby", title.id);
    }

    // Hide background content from screen readers
    this.hideBackgroundContent();
  }

  closeModal(modalElement) {
    const modalIndex = this.activeModals.findIndex(
      (modal) => modal.element === modalElement,
    );

    if (modalIndex !== -1) {
      const modalData = this.activeModals[modalIndex];
      modalData.focusTrap.deactivate();
      this.activeModals.splice(modalIndex, 1);

      // Remove ARIA attributes
      modalElement.removeAttribute("role");
      modalElement.removeAttribute("aria-modal");
      modalElement.removeAttribute("aria-labelledby");

      // Show background content if no modals are open
      if (this.activeModals.length === 0) {
        this.showBackgroundContent();
      }
    }
  }

  handleEscapeKey(event) {
    if (event.key === "Escape" && this.activeModals.length > 0) {
      const topModal = this.activeModals[this.activeModals.length - 1];
      const closeButton = topModal.element.querySelector(
        '.modal-close, [data-dismiss="modal"]',
      );

      if (closeButton) {
        closeButton.click();
      }
    }
  }

  hideBackgroundContent() {
    const mainContent = document.querySelector("main, #app, .v-application");
    if (mainContent) {
      mainContent.setAttribute("aria-hidden", "true");
    }
  }

  showBackgroundContent() {
    const mainContent = document.querySelector("main, #app, .v-application");
    if (mainContent) {
      mainContent.removeAttribute("aria-hidden");
    }
  }
}

/**
 * Form focus management
 */
export class FormFocusManager {
  constructor() {
    this.init();
  }

  init() {
    document.addEventListener(
      "invalid",
      this.handleInvalidField.bind(this),
      true,
    );
    document.addEventListener("submit", this.handleFormSubmit.bind(this));
  }

  handleInvalidField(event) {
    // Focus the first invalid field
    setTimeout(() => {
      event.target.focus();
      this.announceError(event.target);
    }, 100);
  }

  handleFormSubmit(event) {
    const form = event.target;
    const invalidFields = form.querySelectorAll(":invalid");

    if (invalidFields.length > 0) {
      event.preventDefault();
      invalidFields[0].focus();
      this.announceError(invalidFields[0]);
    }
  }

  announceError(field) {
    const errorMessage = this.getErrorMessage(field);
    if (errorMessage) {
      this.announceToScreenReader(`Error: ${errorMessage}`);
    }
  }

  getErrorMessage(field) {
    // Check for custom error message
    const errorElement = document.querySelector(
      `[data-error-for="${field.id}"]`,
    );
    if (errorElement) {
      return errorElement.textContent;
    }

    // Use validation message
    return field.validationMessage;
  }

  announceToScreenReader(message) {
    const announcement = document.createElement("div");
    announcement.setAttribute("aria-live", "assertive");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }
}

/**
 * Table keyboard navigation
 */
export class TableKeyboardNavigation {
  constructor(tableElement) {
    this.table = tableElement;
    this.currentRow = 0;
    this.currentCol = 0;
    this.rows = [];
    this.init();
  }

  init() {
    this.updateRows();
    this.table.addEventListener("keydown", this.handleKeyDown.bind(this));
    this.table.setAttribute("role", "grid");

    // Make table focusable
    if (!this.table.hasAttribute("tabindex")) {
      this.table.setAttribute("tabindex", "0");
    }
  }

  updateRows() {
    this.rows = Array.from(this.table.querySelectorAll("tbody tr"));
    this.rows.forEach((row, index) => {
      row.setAttribute("role", "row");
      row.setAttribute("tabindex", index === 0 ? "0" : "-1");

      const cells = row.querySelectorAll("td, th");
      cells.forEach((cell) => {
        cell.setAttribute("role", "gridcell");
      });
    });
  }

  handleKeyDown(event) {
    const { key } = event;

    switch (key) {
      case "ArrowDown":
        event.preventDefault();
        this.moveDown();
        break;
      case "ArrowUp":
        event.preventDefault();
        this.moveUp();
        break;
      case "Home":
        event.preventDefault();
        this.moveToFirstRow();
        break;
      case "End":
        event.preventDefault();
        this.moveToLastRow();
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        this.activateCurrentRow();
        break;
    }
  }

  moveDown() {
    if (this.currentRow < this.rows.length - 1) {
      this.setCurrentRow(this.currentRow + 1);
    }
  }

  moveUp() {
    if (this.currentRow > 0) {
      this.setCurrentRow(this.currentRow - 1);
    }
  }

  moveToFirstRow() {
    this.setCurrentRow(0);
  }

  moveToLastRow() {
    this.setCurrentRow(this.rows.length - 1);
  }

  setCurrentRow(index) {
    // Remove focus from current row
    if (this.rows[this.currentRow]) {
      this.rows[this.currentRow].setAttribute("tabindex", "-1");
    }

    // Set focus to new row
    this.currentRow = index;
    if (this.rows[this.currentRow]) {
      this.rows[this.currentRow].setAttribute("tabindex", "0");
      this.rows[this.currentRow].focus();
    }
  }

  activateCurrentRow() {
    const currentRow = this.rows[this.currentRow];
    if (currentRow) {
      const button = currentRow.querySelector("button, a");
      if (button) {
        button.click();
      } else {
        // Trigger row click event
        currentRow.click();
      }
    }
  }
}

/**
 * Initialize all focus management systems
 */
export function initializeFocusManagement() {
  // Initialize skip links
  new SkipLinkManager();

  // Initialize keyboard navigation
  new KeyboardNavigationManager();

  // Initialize modal focus management
  const modalManager = new ModalFocusManager();

  // Initialize form focus management
  new FormFocusManager();

  // Initialize table keyboard navigation for all tables
  document.querySelectorAll("table[data-keyboard-nav]").forEach((table) => {
    new TableKeyboardNavigation(table);
  });

  // Add focus-visible polyfill class
  document.body.classList.add("js-focus-visible");

  // Return managers for external use
  return {
    modalManager,
    FocusTrap,
    TableKeyboardNavigation,
  };
}

/**
 * Utility functions for focus management
 */
export const FocusUtils = {
  /**
   * Move focus to element and announce to screen reader
   */
  focusElement(element, announcement = null) {
    if (element) {
      element.focus();
      if (announcement) {
        this.announceToScreenReader(announcement);
      }
    }
  },

  /**
   * Announce message to screen reader
   */
  announceToScreenReader(message, priority = "polite") {
    const announcement = document.createElement("div");
    announcement.setAttribute("aria-live", priority);
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      if (document.body.contains(announcement)) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  },

  /**
   * Check if element is focusable
   */
  isFocusable(element) {
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ];

    return (
      focusableSelectors.some((selector) => element.matches(selector)) &&
      element.offsetWidth > 0 &&
      element.offsetHeight > 0 &&
      !element.hidden
    );
  },

  /**
   * Get all focusable elements within container
   */
  getFocusableElements(container = document) {
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(", ");

    return Array.from(container.querySelectorAll(focusableSelectors)).filter(
      (el) => this.isFocusable(el),
    );
  },
};
