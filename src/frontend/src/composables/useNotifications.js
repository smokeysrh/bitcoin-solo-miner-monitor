/**
 * Notifications Composable
 * 
 * Provides a centralized way to show notifications using the existing
 * snackbar system in App.vue. This composable integrates with the 
 * enhanced settings service for consistent error handling.
 */

import { inject } from 'vue';

/**
 * Use notifications composable
 * Provides methods to show different types of notifications
 */
export function useNotifications() {
  // Try to inject the showSnackbar function from parent component
  const showSnackbar = inject('showSnackbar', null);
  
  // Fallback function if injection fails
  const fallbackNotification = (message, type = 'info') => {
    console.warn('Notification system not available, falling back to console:', { message, type });
    
    // Try to use browser notifications as fallback
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Bitcoin Solo Miner Monitor', {
        body: message,
        icon: '/bitcoin-symbol.png'
      });
    }
  };
  
  const notify = showSnackbar || fallbackNotification;

  /**
   * Show success notification
   */
  const success = (message, timeout = 3000) => {
    notify(message, 'success', timeout);
  };

  /**
   * Show error notification
   */
  const error = (message, timeout = 6000) => {
    notify(message, 'error', timeout);
  };

  /**
   * Show warning notification
   */
  const warning = (message, timeout = 5000) => {
    notify(message, 'warning', timeout);
  };

  /**
   * Show info notification
   */
  const info = (message, timeout = 4000) => {
    notify(message, 'info', timeout);
  };

  /**
   * Show settings-specific success notification
   */
  const settingsSaved = (message = 'Settings saved successfully') => {
    success(message, 3000);
  };

  /**
   * Show settings-specific error notification with enhanced error handling
   */
  const settingsError = (errorObj, customMessage = null) => {
    let message = customMessage || 'Failed to save settings';
    
    // Enhanced error message based on error type
    if (errorObj) {
      if (errorObj.userMessage) {
        message = errorObj.userMessage;
      } else if (errorObj.message) {
        message = errorObj.message;
      }
      
      // Add specific guidance based on error type
      if (errorObj.type === 'VALIDATION_ERROR' && errorObj.validationErrors?.length > 0) {
        const validationMessages = errorObj.validationErrors.map(e => e.message).join(', ');
        message += `\n\nValidation errors: ${validationMessages}`;
      } else if (errorObj.type === 'NETWORK_ERROR') {
        message += '\n\nPlease check your connection and try again.';
      } else if (errorObj.type === 'PERMISSION_ERROR') {
        message += '\n\nYou may need to refresh the page.';
      }
    }
    
    error(message, 8000); // Longer timeout for errors
  };

  /**
   * Handle settings operation with loading and result notifications
   */
  const settingsOperation = async (operationPromise, loadingMessage, successMessage) => {
    // Show loading message
    info(loadingMessage, 1000); // Short timeout for loading message
    
    try {
      const result = await operationPromise;
      
      // Show success message
      settingsSaved(successMessage);
      
      return result;
    } catch (errorObj) {
      // Show error message with enhanced error handling
      settingsError(errorObj);
      
      throw errorObj;
    }
  };

  return {
    success,
    error,
    warning,
    info,
    settingsSaved,
    settingsError,
    settingsOperation,
    // Expose the raw notify function for custom usage
    notify
  };
}