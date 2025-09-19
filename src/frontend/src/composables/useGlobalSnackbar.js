/**
 * Global Snackbar Composable
 * Provides a centralized way to show notifications across the application
 */

import { ref } from 'vue'

// Global reactive state for snackbar
const snackbar = ref({
    show: false,
    text: '',
    color: 'info',
    timeout: 3000
})

export function useGlobalSnackbar() {
    /**
     * Show a snackbar notification
     * @param {string} text - Message to display
     * @param {string} color - Color theme (success, error, warning, info)
     * @param {number} timeout - Auto-hide timeout in milliseconds
     */
    const showSnackbar = (text, color = 'info', timeout = 3000) => {
        snackbar.value = {
            show: true,
            text,
            color,
            timeout
        }
    }

    /**
     * Hide the snackbar
     */
    const hideSnackbar = () => {
        snackbar.value.show = false
    }

    /**
     * Show success message
     * @param {string} text - Success message
     */
    const showSuccess = (text) => {
        showSnackbar(text, 'success')
    }

    /**
     * Show error message
     * @param {string} text - Error message
     */
    const showError = (text) => {
        showSnackbar(text, 'error')
    }

    /**
     * Show warning message
     * @param {string} text - Warning message
     */
    const showWarning = (text) => {
        showSnackbar(text, 'warning')
    }

    /**
     * Show info message
     * @param {string} text - Info message
     */
    const showInfo = (text) => {
        showSnackbar(text, 'info')
    }

    return {
        // State
        snackbar,

        // Methods
        showSnackbar,
        hideSnackbar,
        showSuccess,
        showError,
        showWarning,
        showInfo
    }
}

export default useGlobalSnackbar