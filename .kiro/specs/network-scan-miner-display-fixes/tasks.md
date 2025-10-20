# Implementation Plan - Network Scan and Miner Display Fixes

- [x] 1. Fix Network Scan Dialog Consistency

  - Centralize NetworkScanner dialog management in QuickActions component
  - Remove duplicate dialog implementations from Dashboard and SimpleDashboard
  - Update all network scan entry points to use the centralized dialog
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 1.1 Remove duplicate NetworkScanner dialogs from Dashboard views

  - Remove `networkScannerDialog` ref and `<v-dialog>` wrapper from Dashboard.vue
  - Remove `networkScannerDialog` ref and `<v-dialog>` wrapper from SimpleDashboard.vue
  - Update `handleQuickScanNetwork` methods to rely on QuickActions component
  - _Requirements: 1.1, 1.2_

- [x] 1.2 Update empty state scan buttons to use QuickActions dialog

  - Modify empty state "Scan Network" button in Dashboard.vue to call `handleQuickScanNetwork`
  - Ensure `startDiscovery` method delegates to QuickActions instead of opening separate dialog
  - Test that all scan buttons (Quick Actions, empty state) open the same dialog
  - _Requirements: 1.3, 1.4_

- [x] 2. Remove Duplicate Network Discovery Section

  - Remove the legacy Network Discovery section from Dashboard.vue
  - Clean up associated reactive state and methods
  - Verify all network scanning functionality works through Quick Actions
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.1 Remove Network Discovery section markup and state

  - Delete Network Discovery section markup from Dashboard.vue (lines 196-289)
  - Remove unused reactive refs: `discoveryForm`, `discoveryFormValid`, `discoveryLoading`, `discoveryStatus`
  - Keep `discoveryNetwork` ref for QuickActions prop usage
  - _Requirements: 2.1, 2.2_

- [x] 2.2 Clean up Network Discovery methods

  - Remove `pollDiscoveryStatus` method (no longer needed)
  - Remove `addDiscoveredMiner` method (functionality exists in NetworkScanner)
  - Update `startDiscovery` to delegate to QuickActions handler
  - _Requirements: 2.3, 2.4_

- [x] 3. Fix Network Scan Progress Bar Visualization

  - Diagnose why progress bar color fill is not displaying
  - Fix CSS or Vuetify configuration to show progress bar fill color
  - Ensure progress bar updates smoothly with scan percentage
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.1 Investigate and fix progress bar color rendering

  - Check NetworkScanner.vue progress bar implementation
  - Verify `scanProgress.percentage` is numeric value 0-100
  - Test different Vuetify v-progress-linear configurations (model-value, bg-color)
  - Add explicit CSS styling if needed to force color display
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 3.2 Verify progress bar data flow from composable

  - Check useNetworkScan composable percentage calculation
  - Ensure percentage updates trigger Vue reactivity
  - Test that progress bar fill grows proportionally with percentage
  - _Requirements: 3.3, 3.4_

- [x] 4. Fix NerdQaxe Miner Name and Type Display

  - Implement proper NerdQaxe type detection logic
  - Remove trailing underscores from miner names
  - Differentiate NerdQaxe from Bitaxe in type classification
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4.1 Enhance miner type detection for NerdQaxe

  - Locate miner type detection logic in backend or miners store
  - Add NerdQaxe-specific identification checks (model, hostname, version strings)
  - Ensure NerdQaxe is detected as type "NerdQaxe" not "bitaxe"
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 4.2 Clean up miner name display

  - Implement name cleaning function to remove trailing underscores
  - Apply name cleaning in miners store or display components
  - Test that "NerdQaxe\_" displays as "NerdQaxe"
  - _Requirements: 4.1_

- [x] 5. Fix NerdQaxe Temperature Display in Miner Status Table

  - Normalize temperature field extraction across different miner types
  - Ensure temperature data from API is properly mapped to table display
  - Verify temperature shows actual value instead of "0"
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5.1 Implement temperature field normalization

  - Create temperature extraction function in miners store
  - Check multiple possible temperature field locations (temperature, device_info.temperature, temp)
  - Ensure temperature is converted to numeric type
  - _Requirements: 5.2, 5.3_

- [x] 5.2 Update Dashboard temperature column mapping

  - Verify Dashboard.vue temperature column uses normalized temperature field
  - Test that NerdQaxe temperature displays correctly in table
  - Ensure temperature matches value shown on detail page
  - _Requirements: 5.1, 5.4_

- [ ] 6. Fix Model Name Display on Miner Detail Page

  - Enhance getDeviceInfo method to check alternative model field names
  - Implement fallback to miner type when model field is unavailable
  - Display "NerdQaxe" instead of "N/A" for model name
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 6.1 Enhance device info retrieval logic

  - Update getDeviceInfo method in MinerDetail.vue
  - Add checks for alternative model field names (device_model, hardware_model, product_name)
  - Implement fallback to type name for NerdQaxe when model is unavailable
  - Test that model displays correctly for NerdQaxe and other miner types
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Fix Efficiency Metric Calculation and Display


  - Correct efficiency formula to use W/TH instead of TH/s/W
  - Ensure proper hashrate unit conversion to terahashes
  - Display efficiency in industry-standard format
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7.1 Correct efficiency calculation formula

  - Update calculateEfficiency method in MinerDetail.vue
  - Change formula from (hashrate / power) to (power / hashrate)
  - Ensure hashrate is properly converted to TH/s before calculation
  - Update display format from "TH/s/W" to "W/TH"
  - _Requirements: 7.1, 7.2, 7.5_

- [x] 7.2 Test efficiency calculation with various inputs

  - Test with typical NerdQaxe values (power and hashrate)
  - Verify efficiency displays numeric value instead of "N/A"
  - Ensure proper handling of edge cases (zero power, zero hashrate)
  - _Requirements: 7.3, 7.4_
