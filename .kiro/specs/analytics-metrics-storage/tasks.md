# Implementation Plan

- [x] 1. Integrate TimeSeriesStorage with MinerManager for metrics persistence

  - Add timeseries_storage property to MinerManager
  - Create set_timeseries_storage() method for dependency injection
  - Create \_extract_metrics() helper method to extract relevant metrics from miner status
  - Modify polling logic to save metrics after each successful poll
  - Add error handling to prevent metrics save failures from breaking polling
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 5.2, 5.3_

- [x] 2. Wire TimeSeriesStorage to MinerManager in API Service

  - Modify APIService.**init**() to inject timeseries_storage into miner_manager
  - Verify data_storage.timeseries_storage is properly initialized before injection
  - _Requirements: 5.1_

- [x] 3. Verify DataStorage get_metrics implementation

  - Review existing get_metrics() method in DataStorage
  - Ensure it properly calls timeseries_storage.get_aggregated_metrics()
  - Verify it handles empty results gracefully
  - Test with different time ranges and intervals
  - _Requirements: 1.2, 2.2, 3.2, 4.2_

- [x] 4. Update Analytics time range selector

  - Modify time range options to include 1m, 15m, 1h, 24h, 7d, 30d, custom
  - Remove 6h option from time range selector
  - Update getTimeRange() method to handle new time ranges
  - Update getInterval() method to return appropriate intervals for new ranges

  - Update getTimeUnit() method for chart display
  - _Requirements: 6.1, 6.2_

- [x] 5. Fix custom date picker UX issues

  - Add @change event handler to close date picker on selection
  - Add cancel button to custom date range section
  - Implement cancelCustomRange() method to reset custom selection
  - Test date picker closes properly after selection
  - _Requirements: 6.4, 6.5_

- [x] 6. Add electricity cost setting to Settings page

  - Add electricity cost card to Settings.vue template
  - Create v-text-field for electricity cost input with validation
  - Set default value to 0.13 USD per kWh
  - Add input validation for range 0.01 to 10.00
  - Implement saveElectricityCost() method
  - Load electricity cost from settings on component mount
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 7. Update backend settings schema and API

  - Add electricity_cost field to settings table (if not exists)
  - Verify settings API endpoints handle electricity_cost field
  - Test settings save and retrieve with electricity cost

  - _Requirements: 7.4, 7.5_

- [x] 8. Test metrics persistence end-to-end

  - Start application with a miner

  - Wait for multiple polling cycles
  - Verify metrics are being saved to database
  - Query database directly to confirm data
  - Check for any error logs related to metrics saving
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 9. Using Chrome DevTools
  - Test all time range options
  - Test custom date range selection
  - _Requirements: 1.2, 1.3, 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 6.1, 6.4, 6.5_

- [x] 10. Test electricity cost setting





  - Navigate to Settings page
  - Verify electricity cost field displays with default value
  - Update electricity cost to different values
  - Verify validation works (min/max range)
  - Refresh page and verify setting persists
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
