# Requirements Document

## Introduction

The Analytics feature displays historical data for miners including hashrate, temperature, power consumption, and shares. Currently, these graphs show "No data available" because metrics are not being persisted to the database. This feature will implement proper metrics storage so that historical analytics data can be displayed. Additionally, the time range selector needs improvements and a new electricity cost setting will be added for future cost calculations.

## Glossary

- **Miner Manager**: The backend service responsible for managing miner connections and polling miner data
- **Time Series Storage**: The backend service responsible for storing and retrieving time-series metrics data in SQLite
- **Analytics Dashboard**: The frontend view that displays historical metrics as charts and graphs
- **Metrics**: Numerical data points collected from miners (hashrate, temperature, power, shares, etc.)
- **Polling Cycle**: The periodic process of fetching current status from miners
- **Time Range Selector**: The UI component that allows users to select different time periods for viewing analytics data
- **Electricity Cost Setting**: A user-configurable value representing the cost per kilowatt-hour (kWh) for electricity

## Requirements

### Requirement 1

**User Story:** As a user, I want to see historical hashrate data for my miners so that I can track performance over time

#### Acceptance Criteria

1. WHEN THE Miner Manager polls a miner for status, THE Miner Manager SHALL save hashrate metrics to the Time Series Storage
2. WHEN a user navigates to the Analytics page, THE Analytics Dashboard SHALL retrieve and display hashrate history from the Time Series Storage
3. THE Analytics Dashboard SHALL display hashrate data for the selected time range with appropriate time intervals
4. IF no historical data exists, THEN THE Analytics Dashboard SHALL display a message indicating no data is available yet

### Requirement 2

**User Story:** As a user, I want to see historical temperature data for my miners so that I can monitor thermal performance

#### Acceptance Criteria

1. WHEN THE Miner Manager polls a miner for status, THE Miner Manager SHALL save temperature metrics to the Time Series Storage
2. WHEN a user views the Analytics page, THE Analytics Dashboard SHALL retrieve and display temperature history from the Time Series Storage
3. THE Analytics Dashboard SHALL display temperature data with color coding based on temperature ranges
4. THE temperature data SHALL be displayed in degrees Celsius

### Requirement 3

**User Story:** As a user, I want to see historical power consumption data so that I can track energy usage

#### Acceptance Criteria

1. WHEN THE Miner Manager polls a miner for status, THE Miner Manager SHALL save power consumption metrics to the Time Series Storage
2. WHEN a user views the Analytics page, THE Analytics Dashboard SHALL retrieve and display power consumption history
3. THE power consumption data SHALL be displayed in watts
4. THE Analytics Dashboard SHALL calculate and display efficiency metrics based on hashrate and power data

### Requirement 4

**User Story:** As a user, I want to see historical shares data so that I can track mining success rate

#### Acceptance Criteria

1. WHEN THE Miner Manager polls a miner for status, THE Miner Manager SHALL save accepted and rejected shares metrics to the Time Series Storage
2. WHEN a user views the Analytics page, THE Analytics Dashboard SHALL retrieve and display shares history
3. THE Analytics Dashboard SHALL display both accepted and rejected shares on the same chart
4. THE shares data SHALL be displayed as cumulative counts over time

### Requirement 5

**User Story:** As a user, I want metrics to be saved automatically during normal operation so that I don't lose historical data

#### Acceptance Criteria

1. THE Miner Manager SHALL save metrics to the Time Series Storage during each polling cycle
2. THE metrics saving process SHALL not block or delay the polling cycle
3. IF metrics saving fails, THEN THE Miner Manager SHALL log the error but continue normal operation
4. THE Time Series Storage SHALL handle concurrent metric writes from multiple miners safely

### Requirement 6

**User Story:** As a user, I want improved time range options so that I can view analytics data at different granularities

#### Acceptance Criteria

1. THE Time Range Selector SHALL provide options for 1 minute, 15 minutes, 1 hour, 24 hours, 7 days, 30 days, and custom ranges
2. THE Time Range Selector SHALL NOT include a 6 hour option
3. WHEN a user selects the custom time range option, THE Time Range Selector SHALL display date picker controls
4. WHEN a user selects a date in the custom date picker, THE date picker SHALL close automatically
5. THE custom date picker SHALL include a close button for dismissing without selection

### Requirement 7

**User Story:** As a user, I want to configure my electricity cost so that the system can calculate power-related expenses

#### Acceptance Criteria

1. THE Settings page SHALL include an input field for electricity cost per kilowatt-hour
2. THE electricity cost setting SHALL default to 0.13 USD per kWh (national average)
3. THE electricity cost input SHALL accept decimal values between 0.01 and 10.00
4. WHEN a user updates the electricity cost, THE system SHALL save the value to the application settings
5. THE electricity cost setting SHALL be retrievable by other components for future cost calculations
