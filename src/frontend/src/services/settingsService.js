/**
 * Enhanced Settings Service
 * 
 * Provides comprehensive settings management with proper error handling,
 * loading states, and validation for the Bitcoin Solo Miner Monitor application.
 */

import axios from 'axios';

// API base URL
const API_BASE_URL = '/api';

// Error types for better error handling
export const SettingsErrorTypes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

// Settings validation rules
const VALIDATION_RULES = {
  polling_interval: { min: 5, max: 3600 },
  refresh_interval: { min: 1, max: 300 },
  chart_retention_days: { min: 1, max: 365 },
  theme: { values: ['light', 'dark'] },
  temperature_unit: { values: ['celsius', 'fahrenheit'] },
  default_view: { values: ['dashboard', 'dashboard-simple', 'miners', 'analytics'] }
};

/**
 * Enhanced Settings Service Class
 */
export class SettingsService {
  constructor() {
    this.loadingStates = new Map();
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    this.requestTimeout = 30000; // 30 seconds
    
    // Setup axios interceptors for better error handling
    this.setupAxiosInterceptors();
  }

  /**
   * Check if an endpoint requires authentication
   */
  requiresAuth(method, url) {
    // List of endpoints that require API key authentication
    const authRequiredEndpoints = [
      { method: 'PUT', pattern: '/api/settings' },
      { method: 'POST', pattern: '/api/miners' },
      { method: 'PUT', pattern: '/api/miners/' },
      { method: 'DELETE', pattern: '/api/miners/' },
      { method: 'POST', pattern: '/api/miners/' }, // restart endpoint
      { method: 'PUT', pattern: '/api/email/config' },
      { method: 'POST', pattern: '/api/email/test' },
      { method: 'POST', pattern: '/api/email/send' },
    ];

    const upperMethod = method?.toUpperCase();
    return authRequiredEndpoints.some(endpoint => 
      endpoint.method === upperMethod && url?.includes(endpoint.pattern)
    );
  }

  /**
   * Setup axios interceptors for consistent error handling
   */
  setupAxiosInterceptors() {
    // Request interceptor for timeout and headers
    axios.interceptors.request.use(
      (config) => {
        if (config.url?.startsWith(API_BASE_URL)) {
          config.timeout = this.requestTimeout;
          config.headers['Content-Type'] = 'application/json';
          
          // Add API key for authenticated endpoints (development mode)
          // In production, this should be handled differently
          if (this.requiresAuth(config.method, config.url)) {
            console.log(`SettingsService: Adding API key for ${config.method} ${config.url}`);
            config.headers['Authorization'] = 'Bearer dev-key-12345';
          } else {
            console.log(`SettingsService: No auth required for ${config.method} ${config.url}`);
          }
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    axios.interceptors.response.use(
      (response) => response,
      (error) => {
        const enhancedError = this.enhanceError(error);
        return Promise.reject(enhancedError);
      }
    );
  }

  /**
   * Enhance error with additional context and type classification
   */
  enhanceError(error) {
    const enhancedError = new Error();
    enhancedError.originalError = error;
    
    // Network errors
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        enhancedError.type = SettingsErrorTypes.TIMEOUT_ERROR;
        enhancedError.message = 'Request timed out. Please check your connection and try again.';
        enhancedError.userMessage = 'Connection timeout - please try again';
        enhancedError.retryable = true;
      } else if (error.code === 'NETWORK_ERROR' || error.message.includes('Network Error')) {
        enhancedError.type = SettingsErrorTypes.NETWORK_ERROR;
        enhancedError.message = 'Network connection failed. Please check your internet connection.';
        enhancedError.userMessage = 'Network error - check your connection';
        enhancedError.retryable = true;
      } else {
        enhancedError.type = SettingsErrorTypes.NETWORK_ERROR;
        enhancedError.message = 'Unable to connect to the server. Please try again.';
        enhancedError.userMessage = 'Connection failed - please try again';
        enhancedError.retryable = true;
      }
      return enhancedError;
    }

    // HTTP status code based errors
    const status = error.response.status;
    const data = error.response.data;

    switch (status) {
      case 400:
        enhancedError.type = SettingsErrorTypes.VALIDATION_ERROR;
        enhancedError.message = data?.detail || data?.message || 'Invalid settings data provided.';
        enhancedError.userMessage = 'Invalid settings - please check your input';
        enhancedError.validationErrors = data?.errors || [];
        enhancedError.retryable = false;
        break;

      case 401:
      case 403:
        enhancedError.type = SettingsErrorTypes.PERMISSION_ERROR;
        enhancedError.message = 'You do not have permission to modify settings.';
        enhancedError.userMessage = 'Permission denied - unable to save settings';
        enhancedError.retryable = false;
        break;

      case 422:
        enhancedError.type = SettingsErrorTypes.VALIDATION_ERROR;
        enhancedError.message = 'Settings validation failed.';
        enhancedError.userMessage = 'Invalid settings format';
        enhancedError.validationErrors = data?.errors || [];
        enhancedError.retryable = false;
        break;

      case 429:
        enhancedError.type = SettingsErrorTypes.NETWORK_ERROR;
        enhancedError.message = 'Too many requests. Please wait before trying again.';
        enhancedError.userMessage = 'Rate limited - please wait and try again';
        enhancedError.retryable = true;
        enhancedError.retryAfter = error.response.headers['retry-after'] || 60;
        break;

      case 500:
      case 502:
      case 503:
      case 504:
        enhancedError.type = SettingsErrorTypes.SERVER_ERROR;
        enhancedError.message = 'Server error occurred while saving settings.';
        enhancedError.userMessage = 'Server error - please try again later';
        enhancedError.retryable = true;
        break;

      default:
        enhancedError.type = SettingsErrorTypes.UNKNOWN_ERROR;
        enhancedError.message = data?.detail || data?.message || 'An unexpected error occurred.';
        enhancedError.userMessage = 'Unexpected error - please try again';
        enhancedError.retryable = true;
    }

    enhancedError.status = status;
    enhancedError.timestamp = new Date().toISOString();
    
    return enhancedError;
  }

  /**
   * Validate settings data before sending to server
   */
  validateSettings(settings) {
    const errors = [];
    
    for (const [key, value] of Object.entries(settings)) {
      const rule = VALIDATION_RULES[key];
      if (!rule) continue;

      // Check numeric ranges
      if (rule.min !== undefined && rule.max !== undefined) {
        if (typeof value !== 'number' || value < rule.min || value > rule.max) {
          errors.push({
            field: key,
            message: `${key} must be between ${rule.min} and ${rule.max}`,
            value: value
          });
        }
      }

      // Check allowed values
      if (rule.values && !rule.values.includes(value)) {
        errors.push({
          field: key,
          message: `${key} must be one of: ${rule.values.join(', ')}`,
          value: value
        });
      }
    }

    return {
      isValid: errors.length === 0,
      errors: errors
    };
  }

  /**
   * Set loading state for a specific operation
   */
  setLoadingState(operation, isLoading, details = {}) {
    if (isLoading) {
      this.loadingStates.set(operation, {
        isLoading: true,
        startTime: Date.now(),
        ...details
      });
    } else {
      const currentState = this.loadingStates.get(operation);
      if (currentState) {
        this.loadingStates.set(operation, {
          ...currentState,
          isLoading: false,
          endTime: Date.now(),
          duration: Date.now() - currentState.startTime
        });
      }
    }
  }

  /**
   * Get loading state for a specific operation
   */
  getLoadingState(operation) {
    return this.loadingStates.get(operation) || { isLoading: false };
  }

  /**
   * Check if any settings operation is currently loading
   */
  isAnyOperationLoading() {
    for (const state of this.loadingStates.values()) {
      if (state.isLoading) return true;
    }
    return false;
  }

  /**
   * Get cached settings if available and not expired
   */
  getCachedSettings() {
    const cached = this.cache.get('settings');
    if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
      return cached.data;
    }
    return null;
  }

  /**
   * Cache settings data
   */
  cacheSettings(settings) {
    this.cache.set('settings', {
      data: settings,
      timestamp: Date.now()
    });
  }

  /**
   * Clear settings cache
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Load settings from server with caching and error handling
   */
  async loadSettings() {
    const operationId = 'load_settings';
    
    try {
      this.setLoadingState(operationId, true, { operation: 'Loading settings' });

      // Check cache first
      const cached = this.getCachedSettings();
      if (cached) {
        console.log('SettingsService: Using cached settings');
        return {
          success: true,
          data: cached,
          fromCache: true
        };
      }

      console.log('SettingsService: Loading settings from server');
      const response = await axios.get(`${API_BASE_URL}/settings`);
      
      const settings = response.data;
      this.cacheSettings(settings);

      return {
        success: true,
        data: settings,
        fromCache: false
      };

    } catch (error) {
      console.error('SettingsService: Error loading settings:', error);
      
      return {
        success: false,
        error: error,
        errorType: error.type || SettingsErrorTypes.UNKNOWN_ERROR,
        message: error.userMessage || 'Failed to load settings',
        retryable: error.retryable !== false
      };

    } finally {
      this.setLoadingState(operationId, false);
    }
  }

  /**
   * Save settings to server with comprehensive error handling and validation
   */
  async saveSettings(settings) {
    const operationId = 'save_settings';
    
    try {
      this.setLoadingState(operationId, true, { 
        operation: 'Saving settings',
        settingsCount: Object.keys(settings).length
      });

      console.log('SettingsService: Validating settings before save:', settings);

      // Client-side validation
      const validation = this.validateSettings(settings);
      if (!validation.isValid) {
        const validationError = new Error('Settings validation failed');
        validationError.type = SettingsErrorTypes.VALIDATION_ERROR;
        validationError.userMessage = 'Invalid settings data';
        validationError.validationErrors = validation.errors;
        validationError.retryable = false;
        throw validationError;
      }

      console.log('SettingsService: Sending settings to server');
      const response = await axios.put(`${API_BASE_URL}/settings`, settings);
      
      const updatedSettings = response.data;
      
      // Update cache with new settings
      this.cacheSettings(updatedSettings);
      
      console.log('SettingsService: Settings saved successfully:', updatedSettings);

      return {
        success: true,
        data: updatedSettings,
        message: 'Settings saved successfully'
      };

    } catch (error) {
      console.error('SettingsService: Error saving settings:', error);
      
      // Clear cache on save error to ensure fresh data on next load
      this.clearCache();
      
      return {
        success: false,
        error: error,
        errorType: error.type || SettingsErrorTypes.UNKNOWN_ERROR,
        message: error.userMessage || 'Failed to save settings',
        validationErrors: error.validationErrors || [],
        retryable: error.retryable !== false,
        retryAfter: error.retryAfter
      };

    } finally {
      this.setLoadingState(operationId, false);
    }
  }

  /**
   * Save settings with automatic retry logic
   */
  async saveSettingsWithRetry(settings, maxRetries = 3, baseDelay = 1000) {
    let lastError = null;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      console.log(`SettingsService: Save attempt ${attempt}/${maxRetries}`);
      
      const result = await this.saveSettings(settings);
      
      if (result.success) {
        return result;
      }
      
      lastError = result.error;
      
      // Don't retry if error is not retryable
      if (!result.retryable) {
        console.log('SettingsService: Error is not retryable, stopping attempts');
        break;
      }
      
      // Don't retry on last attempt
      if (attempt === maxRetries) {
        break;
      }
      
      // Calculate delay with exponential backoff
      const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), 10000);
      console.log(`SettingsService: Retrying in ${delay}ms...`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    return {
      success: false,
      error: lastError,
      errorType: lastError?.type || SettingsErrorTypes.UNKNOWN_ERROR,
      message: lastError?.userMessage || 'Failed to save settings after multiple attempts',
      attempts: maxRetries,
      retryable: false // Don't allow further retries after exhausting attempts
    };
  }

  /**
   * Update specific setting with optimistic updates
   */
  async updateSetting(key, value) {
    const operationId = `update_${key}`;
    
    try {
      this.setLoadingState(operationId, true, { 
        operation: `Updating ${key}`,
        key: key,
        value: value
      });

      // Get current settings
      const currentResult = await this.loadSettings();
      if (!currentResult.success) {
        throw currentResult.error;
      }

      const currentSettings = currentResult.data;
      const updatedSettings = {
        ...currentSettings,
        [key]: value
      };

      // Save updated settings
      const saveResult = await this.saveSettings(updatedSettings);
      
      return saveResult;

    } catch (error) {
      console.error(`SettingsService: Error updating ${key}:`, error);
      
      return {
        success: false,
        error: error,
        errorType: error.type || SettingsErrorTypes.UNKNOWN_ERROR,
        message: error.userMessage || `Failed to update ${key}`,
        retryable: error.retryable !== false
      };

    } finally {
      this.setLoadingState(operationId, false);
    }
  }

  /**
   * Reset settings to defaults
   */
  async resetToDefaults() {
    const defaultSettings = {
      polling_interval: 30,
      theme: 'dark',
      chart_retention_days: 30,
      refresh_interval: 10,
      temperature_unit: 'celsius',
      default_view: 'dashboard',
      simple_mode: false
    };

    return await this.saveSettings(defaultSettings);
  }

  /**
   * Get loading states for all operations
   */
  getAllLoadingStates() {
    const states = {};
    for (const [operation, state] of this.loadingStates.entries()) {
      states[operation] = state;
    }
    return states;
  }

  /**
   * Clear all loading states
   */
  clearLoadingStates() {
    this.loadingStates.clear();
  }

  /**
   * Export settings for backup
   */
  async exportSettings() {
    const result = await this.loadSettings();
    if (result.success) {
      const exportData = {
        settings: result.data,
        exportedAt: new Date().toISOString(),
        version: '1.0'
      };
      
      return {
        success: true,
        data: exportData
      };
    }
    
    return result;
  }

  /**
   * Import settings from backup
   */
  async importSettings(importData) {
    try {
      if (!importData.settings) {
        throw new Error('Invalid import data: missing settings');
      }

      const result = await this.saveSettings(importData.settings);
      
      if (result.success) {
        console.log('SettingsService: Settings imported successfully');
      }
      
      return result;

    } catch (error) {
      console.error('SettingsService: Error importing settings:', error);
      
      return {
        success: false,
        error: error,
        errorType: SettingsErrorTypes.VALIDATION_ERROR,
        message: 'Failed to import settings: ' + error.message,
        retryable: false
      };
    }
  }
}

// Create and export singleton instance
export const settingsService = new SettingsService();

// Export for direct usage
export default settingsService;