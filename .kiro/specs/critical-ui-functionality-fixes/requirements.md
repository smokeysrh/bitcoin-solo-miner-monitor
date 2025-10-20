# Requirements Document

## Introduction

This specification addresses critical functionality issues in the Bitcoin Miner Management application that prevent users from effectively monitoring and managing their mining operations. The issues span multiple core features including the refresh mechanism, real-time analytics updates, timeframe selection, cross-page data synchronization, tab navigation, and network page functionality. These bugs significantly impact the user experience and the application's ability to provide real-time mining insights.

## Glossary

- **Application**: The Bitcoin Miner Management web application
- **Analytics_System**: The component responsible for collecting, processing, and displaying mining metrics and charts
- **Refresh_Mechanism**: The system component that updates miner data on user request
- **Timeframe_Selector**: The UI component that allows users to filter analytics data by time periods
- **Time_Range**: The total span of historical data displayed (e.g., last 24 hours, last 7 days, last 30 days)
- **Time_Increment**: The granularity of individual data points on charts (e.g., 1 minute, 15 minutes, 1 hour, 1 day)
- **Miners_Tab**: The main miners page containing Overview, Performance, Pool, and Settings sub-tabs
- **Network_Page**: The page displaying network scanning and discovery functionality
- **Chart_Component**: Visual representation of mining metrics data
- **Analytics_Preview**: A condensed view of key performance charts on the miner details page with a link to full analytics
- **Metrics_Update**: The process of saving new mining data to the database
- **Real-time_Update**: The automatic refresh of UI components when new data becomes available
- **Network_Health_Monitor**: The system component that tracks and displays home network performance metrics
- **Bitcoin_Node**: The user's local Bitcoin node or remote pool server that miners connect to for mining operations
- **Network_Latency**: The round-trip time for data packets between miners and the Bitcoin node or pool
- **Packet_Loss**: The percentage of network packets that fail to reach their destination
- **Network_Stability**: A measure of consistent network performance over time including uptime and connection reliability

## Requirements

### Requirement 1

**User Story:** As a mining operator, I want to manually refresh miner data using the refresh button, so that I can get the latest information on demand without waiting for automatic updates

#### Acceptance Criteria

1. WHEN the user clicks the refresh button, THE Refresh_Mechanism SHALL trigger an API call to the designated refresh endpoint
2. WHEN the refresh API call completes successfully, THE Application SHALL update all displayed miner data within 2 seconds
3. IF the refresh API endpoint does not exist, THEN THE Application SHALL create and wire the endpoint to the refresh functionality
4. WHILE the refresh operation is in progress, THE Refresh_Mechanism SHALL display a loading indicator to the user
5. IF the refresh operation fails, THEN THE Application SHALL display an error message indicating the failure reason

### Requirement 2

**User Story:** As a mining operator, I want analytics charts to update automatically when new metrics are saved, so that I can monitor mining performance in real-time without manual intervention

#### Acceptance Criteria

1. WHEN new metrics data is saved to the database, THE Analytics_System SHALL detect the update within 1 second
2. WHEN a metrics update is detected, THE Analytics_System SHALL refresh all Chart_Components on the Analytics page automatically
3. THE Analytics_System SHALL maintain chart update frequency without degrading application performance
4. WHILE charts are updating, THE Analytics_System SHALL preserve the user's current view and zoom level
5. IF a chart update fails, THEN THE Analytics_System SHALL log the error and retry the update once after 3 seconds

### Requirement 3

**User Story:** As a mining operator, I want to switch between different time ranges and time increments in the Analytics section instantly, so that I can view mining performance at different scales and granularities similar to trading chart interfaces

#### Acceptance Criteria

1. WHEN the user clicks a time range button, THE Timeframe_Selector SHALL immediately update all charts to display the selected historical period without requiring an Apply button
2. WHEN the user clicks a time increment button, THE Timeframe_Selector SHALL immediately update all charts to display data points at the selected granularity
3. THE Timeframe_Selector SHALL provide separate controls for time range selection (e.g., 24h, 7d, 30d) and time increment selection (e.g., 1m, 15m, 1h, 1d)
4. WHEN either time range or time increment is changed, THE Timeframe_Selector SHALL visually highlight the active selection for both controls
5. THE Analytics_System SHALL load and display updated chart data within 1.5 seconds of any selection change
6. IF insufficient data exists for the selected combination of range and increment, THEN THE Analytics_System SHALL display a message indicating the data limitation

### Requirement 4

**User Story:** As a mining operator, I want to see an Analytics Preview section with key performance charts on the individual miner details page, so that I can quickly assess miner health and access detailed analytics when needed

#### Acceptance Criteria

1. WHEN the user clicks on a miner and navigates to the miner details page, THE Application SHALL display an Analytics Preview section containing Hashrate, Temperature, and Power Consumption charts populated with recent miner data
2. WHEN the user views the Analytics Preview section, THE Application SHALL display a "See Full Analytics" button that navigates to the Analytics page
3. WHEN the "See Full Analytics" button is clicked, THE Application SHALL navigate to the Analytics page with the current miner pre-selected
4. WHEN new metrics are saved for the selected miner, THE Application SHALL update all preview charts automatically
5. THE Analytics Preview charts SHALL display a condensed time range appropriate for quick overview (e.g., last 6 hours)
6. IF chart data fails to load for a specific miner, THEN THE Application SHALL display an error message indicating which data is unavailable

### Requirement 5

**User Story:** As a mining operator, I want a streamlined miner details page without unnecessary navigation elements, so that I can view all miner information in a single, cohesive overview

#### Acceptance Criteria

1. WHEN the user navigates to the miner details page, THE Application SHALL display all miner information (overview, performance, pool, settings) in a single scrollable view
2. THE Application SHALL remove the tab-style navigation buttons (Overview, Performance, Pool, Settings) from the miner details page
3. THE Application SHALL organize miner information in a logical, vertically-stacked layout that flows naturally
4. THE Application SHALL ensure all existing miner information sections remain accessible without requiring navigation
5. THE Application SHALL maintain consistent styling and spacing throughout the unified miner details page

### Requirement 6

**User Story:** As a mining operator, I want the Network Topology page to accurately display and update my mining network visualization, so that I can understand the structure and status of my mining infrastructure at a glance

#### Acceptance Criteria

1. WHEN the user navigates to the Network page, THE Network_Page SHALL display an interactive D3.js visualization showing all miners connected to a central router node
2. WHEN the user clicks the "Refresh Network" button, THE Network_Page SHALL fetch updated miner data and redraw the visualization within 2 seconds
3. WHEN the user changes the layout type (Force-Directed, Radial, Grid, Tree), THE Network_Page SHALL immediately update the visualization to use the selected layout algorithm
4. WHEN the user clicks on a miner node in the visualization, THE Network_Page SHALL display a dialog with detailed miner information including status, hashrate, temperature, and uptime
5. THE Network_Page SHALL display accurate network statistics including total miners, online/offline counts, total hashrate, and miner type distribution
6. WHEN the user clicks "Export Image", THE Network_Page SHALL generate and download a PNG image of the current network visualization

### Requirement 7

**User Story:** As a solo mining operator, I want to monitor my home network health and stability on the Network Topology page, so that I can identify and resolve network issues that may impact mining performance

#### Acceptance Criteria

1. WHEN the user views the Network Topology page, THE Network_Health_Monitor SHALL display network latency measurements to the Bitcoin_Node or pool for each connected miner
2. WHEN the user views the Network Topology page, THE Network_Health_Monitor SHALL display packet loss percentage for each miner connection
3. WHEN the user views the Network Topology page, THE Network_Health_Monitor SHALL display connection uptime duration for each miner
4. THE Network_Health_Monitor SHALL visually indicate network health status on miner nodes using color coding (green for healthy, yellow for degraded, red for poor)
5. WHEN the user views network statistics, THE Network_Health_Monitor SHALL display overall network stability indicators including average latency, total packet loss rate, and network jitter
6. THE Network_Health_Monitor SHALL update network health metrics automatically at regular intervals without requiring manual refresh
7. WHEN a miner experiences high latency or packet loss, THE Network_Health_Monitor SHALL display a warning indicator on the affected miner node
8. IF network health data cannot be collected for a miner, THEN THE Network_Health_Monitor SHALL display "N/A" for unavailable metrics
