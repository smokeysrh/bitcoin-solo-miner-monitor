# Requirements Document

## Introduction

This feature addresses critical issues with the polling interval settings and WebSocket stability in the MinervaOS application. Currently, user-configured polling intervals are not being applied to components, resulting in excessive API requests that overwhelm the browser and cause WebSocket disconnections during network scans. This fix will ensure settings are properly applied, reduce redundant polling, and maintain stable WebSocket connections during long-running operations.

## Glossary

- **Frontend Application**: The Vue.js-based user interface that displays miner data and network scan results
- **Settings Store**: The Pinia store that manages user configuration including refresh_interval and ui_refresh_interval
- **Polling Interval**: The time delay between automatic HTTP requests to fetch updated miner data
- **WebSocket Connection**: The persistent bidirectional connection between Frontend Application and Backend Server for real-time updates
- **Network Scan**: A long-running operation that discovers miners on the local network
- **Component Lifecycle**: The sequence of mount, update, and unmount events in Vue.js components
- **Backend Server**: The Python FastAPI server that provides REST APIs and WebSocket endpoints

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want my polling interval settings to be applied immediately when I change them, so that I can control the frequency of API requests

#### Acceptance Criteria

1. WHEN a user changes the refresh_interval setting in the Settings page, THE Frontend Application SHALL update all active polling intervals within 1 second
2. WHEN a component mounts, THE Frontend Application SHALL read the current refresh_interval value from Settings Store
3. WHEN the refresh_interval setting changes, THE Frontend Application SHALL clear existing intervals and create new intervals with the updated value
4. WHEN a user sets refresh_interval to 120 seconds, THE Frontend Application SHALL make HTTP requests to /api/miners no more frequently than once every 120 seconds
5. THE Frontend Application SHALL maintain only one active polling interval per component instance

### Requirement 2

**User Story:** As a system administrator, I want to eliminate redundant polling from multiple components, so that the application uses minimal network resources

#### Acceptance Criteria

1. WHEN multiple view components are mounted simultaneously, THE Frontend Application SHALL coordinate polling to prevent duplicate requests within the same 5-second window
2. WHEN the Dashboard view is active, THE Frontend Application SHALL fetch miner data at the configured refresh_interval
3. WHEN a user navigates between views, THE Frontend Application SHALL clean up polling intervals from unmounted components within 1 second
4. THE Frontend Application SHALL log a warning message when multiple polling sources are detected for the same API endpoint
5. WHEN WebSocket connection is active and broadcasting updates, THE Frontend Application SHALL reduce HTTP polling frequency by 50 percent

### Requirement 3

**User Story:** As a system administrator, I want the WebSocket connection to remain stable during network scans, so that I receive real-time progress updates

#### Acceptance Criteria

1. WHEN a network scan is in progress, THE Frontend Application SHALL respond to WebSocket ping messages within 5 seconds
2. WHEN the browser event loop is busy processing HTTP requests, THE Frontend Application SHALL prioritize WebSocket heartbeat responses
3. WHEN the Backend Server sends a ping message, THE Frontend Application SHALL send a pong response before processing any queued HTTP responses
4. THE Frontend Application SHALL maintain WebSocket connection for at least 300 seconds during active network scans
5. WHEN WebSocket connection is lost during a scan, THE Frontend Application SHALL display a reconnection indicator to the user

### Requirement 4

**User Story:** As a developer, I want to reduce console logging spam, so that I can effectively debug issues when they occur

#### Acceptance Criteria

1. THE Frontend Application SHALL NOT log authentication bypass messages for routine API requests
2. WHEN an API request fails, THE Frontend Application SHALL log error details including status code and endpoint
3. THE Frontend Application SHALL log settings changes at info level including old and new values
4. THE Frontend Application SHALL log WebSocket connection state changes at info level
5. WHEN debug mode is disabled, THE Frontend Application SHALL suppress verbose logging for successful operations

### Requirement 5

**User Story:** As a system administrator, I want the backend to broadcast updates only when data changes, so that the system uses minimal resources

#### Acceptance Criteria

1. WHEN miner data has not changed since the last broadcast, THE Backend Server SHALL NOT send a miners_update message
2. WHEN zero miners are connected, THE Backend Server SHALL broadcast miners_update no more frequently than once every 30 seconds
3. WHEN miner data changes, THE Backend Server SHALL broadcast miners_update within 2 seconds
4. THE Backend Server SHALL compare current miner state with previous broadcast state before sending updates
5. THE Backend Server SHALL log the number of changed fields when broadcasting miners_update at debug level

### Requirement 6

**User Story:** As a system administrator, I want to verify that polling settings work correctly, so that I can confirm the fixes are effective

#### Acceptance Criteria

1. WHEN a user changes refresh_interval to 120 seconds, THE Frontend Application SHALL display a confirmation message indicating the new interval is active
2. WHEN viewing the browser network tab, THE Frontend Application SHALL show request timestamps that match the configured refresh_interval within 2 seconds
3. WHEN a network scan completes successfully, THE Frontend Application SHALL display all discovered miners in the results table
4. THE Frontend Application SHALL provide a diagnostic page showing current polling intervals for all active components
5. WHEN WebSocket connection is active, THE Frontend Application SHALL display connection status and last heartbeat timestamp in the UI
