/**
 * Global Clipboard Service
 * Provides universal clipboard functionality with browser compatibility checks
 * and consistent error handling across the application
 */

class ClipboardService {
  constructor() {
    this.isClipboardSupported = this.checkClipboardSupport()
  }

  /**
   * Check if the Clipboard API is supported in the current browser
   * @returns {boolean} True if clipboard API is supported
   */
  checkClipboardSupport() {
    return (
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === 'function' &&
      window.isSecureContext
    )
  }

  /**
   * Copy text to clipboard using the most appropriate method
   * @param {string} text - Text to copy to clipboard
   * @returns {Promise<boolean>} Promise that resolves to true if successful
   */
  async copyToClipboard(text) {
    if (!text || typeof text !== 'string') {
      throw new Error('Invalid text provided for clipboard operation')
    }

    try {
      if (this.isClipboardSupported) {
        // Use modern Clipboard API
        await navigator.clipboard.writeText(text)
        return true
      } else {
        // Fallback to execCommand for older browsers
        return this.fallbackCopyToClipboard(text)
      }
    } catch (error) {
      // Handle permission denied and other clipboard errors
      if (error.name === 'NotAllowedError') {
        throw new Error('Clipboard access denied. Please allow clipboard permissions.')
      } else if (error.name === 'SecurityError') {
        throw new Error('Clipboard access requires a secure context (HTTPS).')
      } else {
        // Try fallback method if modern API fails
        try {
          return this.fallbackCopyToClipboard(text)
        } catch (fallbackError) {
          throw new Error('Failed to copy to clipboard. Please copy manually.')
        }
      }
    }
  }

  /**
   * Fallback clipboard copy method using execCommand
   * @param {string} text - Text to copy to clipboard
   * @returns {boolean} True if successful
   */
  fallbackCopyToClipboard(text) {
    try {
      // Create temporary textarea element
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      textArea.setAttribute('readonly', '')
      textArea.setAttribute('aria-hidden', 'true')
      
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      
      // Execute copy command
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      
      if (!successful) {
        throw new Error('execCommand copy failed')
      }
      
      return true
    } catch (error) {
      throw new Error('Fallback copy method failed')
    }
  }

  /**
   * Copy donation address with predefined success message
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async copyDonationAddress() {
    const donationAddress = 'bc1qnce06pg2gqewjvjmfavwrjt5f4zc37k5d26c6e'
    
    try {
      await this.copyToClipboard(donationAddress)
      return {
        success: true,
        message: 'Donation address copied to clipboard! Thank you for your support! 🧡'
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to copy donation address: ${error.message}`
      }
    }
  }

  /**
   * Generic copy method with custom success/error messages
   * @param {string} text - Text to copy
   * @param {string} successMessage - Custom success message
   * @param {string} errorPrefix - Prefix for error messages
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async copyWithFeedback(text, successMessage = 'Copied to clipboard!', errorPrefix = 'Copy failed') {
    try {
      await this.copyToClipboard(text)
      return {
        success: true,
        message: successMessage
      }
    } catch (error) {
      return {
        success: false,
        message: `${errorPrefix}: ${error.message}`
      }
    }
  }

  /**
   * Check if clipboard permissions are granted
   * @returns {Promise<boolean>} True if permissions are granted
   */
  async checkPermissions() {
    if (!navigator.permissions || !navigator.permissions.query) {
      // Permissions API not supported, assume allowed
      return true
    }

    try {
      const permission = await navigator.permissions.query({ name: 'clipboard-write' })
      return permission.state === 'granted' || permission.state === 'prompt'
    } catch (error) {
      // Permission query failed, assume allowed
      return true
    }
  }

  /**
   * Get clipboard capability information
   * @returns {Object} Information about clipboard capabilities
   */
  getCapabilities() {
    return {
      isSupported: this.isClipboardSupported,
      hasPermissionsAPI: !!(navigator.permissions && navigator.permissions.query),
      isSecureContext: window.isSecureContext,
      hasClipboardAPI: !!(navigator.clipboard && navigator.clipboard.writeText),
      hasExecCommand: !!document.execCommand
    }
  }
}

// Create and export singleton instance
const clipboardService = new ClipboardService()

export default clipboardService
export { ClipboardService }