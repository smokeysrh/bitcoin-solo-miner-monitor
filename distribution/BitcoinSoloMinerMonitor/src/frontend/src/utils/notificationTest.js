/**
 * Notification System Test Utility
 * 
 * This utility helps test that all notifications are working properly
 * across the application using the global snackbar system.
 */

import { useGlobalSnackbar } from '../composables/useGlobalSnackbar'

export function testNotificationSystem() {
  const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar()
  
  console.log('Testing notification system...')
  
  // Test all notification types with a delay between each
  setTimeout(() => {
    showSuccess('Success notification test')
  }, 500)
  
  setTimeout(() => {
    showError('Error notification test')
  }, 1500)
  
  setTimeout(() => {
    showWarning('Warning notification test')
  }, 2500)
  
  setTimeout(() => {
    showInfo('Info notification test')
  }, 3500)
  
  console.log('Notification tests scheduled - check UI for snackbars')
}

/**
 * Check if a component is using the global snackbar system correctly
 */
export function validateNotificationUsage(componentName, hasGlobalSnackbar = false) {
  if (!hasGlobalSnackbar) {
    console.warn(`⚠️  ${componentName} may not be using the global snackbar system`)
    return false
  }
  
  console.log(`✅ ${componentName} is using the global snackbar system`)
  return true
}

export default {
  testNotificationSystem,
  validateNotificationUsage
}