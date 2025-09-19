/**
 * Vue Composable for Clipboard Operations
 * Provides reactive clipboard functionality with notification integration
 */

import { ref } from 'vue'
import clipboardService from '@/services/clipboardService'

export function useClipboard() {
  const isLoading = ref(false)
  const lastError = ref(null)
  const lastSuccess = ref(null)

  /**
   * Copy text to clipboard with loading state and error handling
   * @param {string} text - Text to copy
   * @param {string} successMessage - Custom success message
   * @param {string} errorPrefix - Prefix for error messages
   * @returns {Promise<{success: boolean, message: string}>}
   */
  const copy = async (text, successMessage, errorPrefix) => {
    isLoading.value = true
    lastError.value = null
    lastSuccess.value = null

    try {
      const result = await clipboardService.copyWithFeedback(text, successMessage, errorPrefix)
      
      if (result.success) {
        lastSuccess.value = result.message
      } else {
        lastError.value = result.message
      }
      
      return result
    } catch (error) {
      const errorMessage = `Copy failed: ${error.message}`
      lastError.value = errorMessage
      return {
        success: false,
        message: errorMessage
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Copy donation address with predefined messaging
   * @returns {Promise<{success: boolean, message: string}>}
   */
  const copyDonationAddress = async () => {
    isLoading.value = true
    lastError.value = null
    lastSuccess.value = null

    try {
      const result = await clipboardService.copyDonationAddress()
      
      if (result.success) {
        lastSuccess.value = result.message
      } else {
        lastError.value = result.message
      }
      
      return result
    } catch (error) {
      const errorMessage = `Failed to copy donation address: ${error.message}`
      lastError.value = errorMessage
      return {
        success: false,
        message: errorMessage
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get clipboard capabilities
   * @returns {Object} Clipboard capability information
   */
  const getCapabilities = () => {
    return clipboardService.getCapabilities()
  }

  /**
   * Check clipboard permissions
   * @returns {Promise<boolean>} True if permissions are available
   */
  const checkPermissions = async () => {
    try {
      return await clipboardService.checkPermissions()
    } catch (error) {
      console.warn('Failed to check clipboard permissions:', error)
      return false
    }
  }

  /**
   * Clear error and success states
   */
  const clearState = () => {
    lastError.value = null
    lastSuccess.value = null
  }

  return {
    // State
    isLoading,
    lastError,
    lastSuccess,

    // Methods
    copy,
    copyDonationAddress,
    getCapabilities,
    checkPermissions,
    clearState
  }
}

export default useClipboard