# Requirements Document - Network Scan and Miner Display Fixes

## Introduction

This specification addresses critical bugs in the Network Scan functionality and miner display components of the Bitcoin Solo Miner Monitor application. These fixes focus on ensuring consistent user interface behavior, accurate data display, and proper visual feedback during network scanning operations.

## Glossary

- **Network Scan Dialog**: A modal window that displays network scanning progress and results
- **Dashboard**: The main application view showing miner status and system information
- **Network Discovery Section**: A UI component on the dashboard for initiating network scans
- **Quick Actions Section**: A UI component providing quick access to common operations
- **Progress Bar**: A visual indicator showing scan completion percentage
- **NerdQaxe**: A specific type of Bitcoin mining device based on open-source Bitaxe hardware/firmware
- **Miner Status Section**: Dashboard component displaying a list of connected miners with their current status
- **Miner Detail Page**: A dedicated page showing comprehensive information about a specific miner
- **Temperature Column**: A table column displaying the current operating temperature of a miner
- **Efficiency Metric**: A performance measurement calculated as watts per terahash (W/TH)

## Requirements

### Requirement 1: Consistent Network Scan Dialog Display

**User Story:** As a user, I want the Network Scan dialog to appear consistently whenever I click any Network Scan button, so that I have a predictable and reliable scanning experience.

#### Acceptance Criteria

1. WHEN the user clicks any Network Scan button in the application, THEN the System SHALL display the Network Scan dialog window
2. WHEN the Network Scan dialog is displayed, THEN the System SHALL present identical layout and functionality regardless of which button triggered it
3. WHEN the user initiates a scan from Quick Actions, THEN the System SHALL display the same Network Scan dialog as other entry points
4. WHEN the user initiates a scan from any location, THEN the System SHALL ensure the dialog appears with proper z-index and visibility

### Requirement 2: Remove Duplicate Network Discovery Section

**User Story:** As a user, I want a clean dashboard without redundant functionality, so that I can navigate the interface efficiently without confusion.

#### Acceptance Criteria

1. WHEN the user views the Dashboard page, THEN the System SHALL display only one Network Discovery interface in the Quick Actions section
2. WHEN the Network Discovery section at the bottom of the Dashboard is removed, THEN the System SHALL maintain all network scanning functionality through Quick Actions
3. WHEN the duplicate section is removed, THEN the System SHALL not leave any orphaned code or styling artifacts
4. WHEN the user accesses network scanning features, THEN the System SHALL provide the functionality exclusively through the Quick Actions section

### Requirement 3: Functional Network Scan Progress Bar

**User Story:** As a user, I want to see the progress bar fill with color as the network scan progresses, so that I have clear visual feedback about the scanning status.

#### Acceptance Criteria

1. WHEN a network scan is in progress, THEN the System SHALL update the progress bar fill color in real-time
2. WHEN the scan percentage increases, THEN the System SHALL increase the colored portion of the progress bar proportionally
3. WHEN the progress bar updates, THEN the System SHALL maintain synchronization with the percentage counter and IP counter
4. WHEN the scan completes, THEN the System SHALL display the progress bar at 100% fill
5. WHILE the scan is running, THEN the System SHALL provide smooth visual transitions for progress bar updates

### Requirement 4: Accurate NerdQaxe Miner Display

**User Story:** As a user, I want to see accurate information about my NerdQaxe miner in the Miner Status section, so that I can monitor its performance correctly.

#### Acceptance Criteria

1. WHEN a NerdQaxe miner is displayed in the Name column, THEN the System SHALL show "NerdQaxe" without any trailing underscores
2. WHEN a NerdQaxe miner is displayed in the Type column, THEN the System SHALL show "NerdQaxe" as the type instead of "bitaxe"
3. WHEN the System detects a NerdQaxe miner, THEN the System SHALL properly differentiate it from standard Bitaxe miners in the type classification
4. WHEN miner type is determined, THEN the System SHALL use device-specific identification logic to distinguish between NerdQaxe and Bitaxe variants

### Requirement 5: Accurate Temperature Display for NerdQaxe

**User Story:** As a user, I want to see the current temperature of my NerdQaxe miner in the Miner Status section, so that I can monitor its thermal performance.

#### Acceptance Criteria

1. WHEN a NerdQaxe miner is displayed in the Miner Status section, THEN the System SHALL show the current temperature value in the Temperature column
2. WHEN temperature data is available from the miner API, THEN the System SHALL display the temperature instead of showing "0"
3. WHEN the System retrieves miner data, THEN the System SHALL correctly parse and map the temperature field from the API response
4. WHEN temperature is displayed, THEN the System SHALL use the same data source that populates the miner detail page

### Requirement 6: Correct Model Name Display on Miner Detail Page

**User Story:** As a user, I want to see the correct model name for my NerdQaxe miner on its detail page, so that I can identify the device accurately.

#### Acceptance Criteria

1. WHEN the user views the NerdQaxe miner detail page, THEN the System SHALL display the device model name instead of "N/A"
2. WHEN the System retrieves miner information, THEN the System SHALL correctly parse the model name field from the API response
3. WHEN model information is unavailable, THEN the System SHALL display a meaningful fallback value based on detected miner type
4. WHEN the detail page loads, THEN the System SHALL use the same identification logic that determines the miner type

### Requirement 7: Correct Efficiency Metric Calculation and Display

**User Story:** As a user, I want to see the efficiency metric calculated and displayed correctly on the miner detail page, so that I can evaluate my miner's power performance.

#### Acceptance Criteria

1. WHEN the System calculates efficiency, THEN the System SHALL use the formula: efficiency = power_watts / hashrate_terahashes
2. WHEN efficiency is displayed, THEN the System SHALL show the value in watts per terahash (W/TH) format
3. WHEN the System has valid power and hashrate data, THEN the System SHALL display a numeric efficiency value on the miner detail page
4. WHEN power or hashrate data is unavailable, THEN the System SHALL display "N/A" for the efficiency metric
5. IF the current display format is TH/s/W, THEN the System SHALL correct the calculation logic to use W/TH instead
