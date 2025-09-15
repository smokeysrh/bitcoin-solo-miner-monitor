# Bitcoin Logo Reimplementation Implementation Plan

## Phase 1: Core Infrastructure

- [x] 1. Create BitcoinLogo Vue component with smart size logic
  - Create src/frontend/src/components/BitcoinLogo.vue with props for size, variant, animated, and accessibility
  - Implement computed property for logoSrc that uses SVG for sizes ≤32px and PNG for larger sizes
  - Add size mapping for preset values (xs: 16px, sm: 24px, md: 32px, lg: 48px, xl: 64px, hero: 96px)
  - Include error handling with onLogoError and onLogoLoad methods
  - Add proper TypeScript prop validation and default values
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Implement backend API endpoints for Bitcoin logo serving
  - Add /bitcoin-symbol.svg endpoint in src/backend/api/api_service.py that serves assets/bitcoin-symbol.svg
  - Add /bitcoin-symbol.png endpoint that serves assets/bitcoin-symbol.png  
  - Include proper MIME types (image/svg+xml, image/png) and caching headers
  - Implement comprehensive error handling for missing files and permissions
  - Add ETag support for efficient caching
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Create Bitcoin logo CSS utilities and styling system
  - Create src/frontend/src/assets/css/bitcoin-logo.css with size variant classes
  - Implement .bitcoin-logo--xs through .bitcoin-logo--hero size classes
  - Add visual variant styles (.bitcoin-logo--glow, .bitcoin-logo--subtle)
  - Include animation keyframes for .bitcoin-logo--animated
  - Add responsive design breakpoints for mobile optimization
  - Import bitcoin-logo.css in main.css
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4. Set up component unit testing framework
  - Create tests/unit/components/BitcoinLogo.test.js with Vue Test Utils
  - Write tests for size prop validation and logoSrc computation
  - Test SVG vs PNG selection logic based on size
  - Add tests for error handling (onLogoError, onLogoLoad events)
  - Test accessibility attributes and aria-label functionality
  - _Requirements: 10.1, 10.4_

## Phase 2: Application Integration

- [x] 5. Integrate BitcoinLogo in main application header
  - Update src/frontend/src/App.vue to import and use BitcoinLogo component
  - Add logo to app bar with size="sm" and proper spacing
  - Add logo to navigation drawer header with size="md"
  - Ensure logos are hidden when isSetupRoute is true
  - Test responsive behavior and alignment
  - Run npm run build to implement the new changes for testing
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Update FirstRunWizard header with Bitcoin logo
  - Modify src/frontend/src/components/FirstRunWizard.vue to include BitcoinLogo
  - Replace placeholder comment with BitcoinLogo component using size="lg" and variant="glow"
  - Add proper spacing and alignment in wizard-header section
  - Ensure logo displays correctly with wizard title and subtitle
  - Test logo visibility across all wizard steps
  - Run npm run build to implement the new changes for testing
  - _Requirements: 4.1, 4.4_

- [x] 7. Implement welcome screen hero logo
  - Update src/frontend/src/components/wizard/WelcomeScreen.vue with hero BitcoinLogo
  - Replace placeholder with BitcoinLogo using size="hero", variant="glow", and animated="true"
  - Add proper CSS classes for centering and visual effects
  - Ensure logo scales appropriately on mobile devices
  - Test animation performance and accessibility compliance
  - Run npm run build to implement the new changes for testing
  - _Requirements: 4.2, 4.4, 4.5_

- [x] 8. Add logo to network discovery screen
  - Update src/frontend/src/components/wizard/NetworkDiscoveryScreen.vue
  - Replace placeholder with BitcoinLogo using size="md" and appropriate styling
  - Ensure logo complements the discovery screen layout
  - Test logo positioning and responsive behavior
  - Run npm run build to implement the new changes for testing
  - _Requirements: 4.3, 4.4_

## Phase 3: Page Integration

- [x] 9. Implement About page hero logo section
  - Update src/frontend/src/views/About.vue to include hero BitcoinLogo
  - Replace placeholder comment with BitcoinLogo using size="xl"
  - Ensure proper centering and spacing in bitcoin-hero section
  - Add responsive scaling for different screen sizes
  - Test visual hierarchy with page title and subtitle
  - Run npm run build to implement the new changes for testing
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Update BitcoinLoadingSpinner component
  - Modify src/frontend/src/components/BitcoinLoadingSpinner.vue to use BitcoinLogo
  - Replace logo placeholder with BitcoinLogo component using computed logoSize
  - Ensure logo is properly centered within the spinning ring
  - Maintain existing spinner functionality and animations
  - Test loading spinner across different size variants
  - Run npm run build to implement the new changes for testing
  - _Requirements: 6.1, 6.3, 6.5_

- [x] 11. Update BitcoinSuccessMessage component  
  - Modify src/frontend/src/components/BitcoinSuccessMessage.vue to include BitcoinLogo
  - Replace logo placeholder with BitcoinLogo using size="sm" and variant="glow"
  - Ensure logo works with success checkmark overlay
  - Maintain existing success message functionality
  - Test logo integration with different message layouts
  - Run npm run build to implement the new changes for testing
  - _Requirements: 6.2, 6.4, 6.5_

- [x] 12. Update EasterEggTest component
  - Modify src/frontend/src/components/EasterEggTest.vue to include BitcoinLogo
  - Replace placeholder with BitcoinLogo using size="md"
  - Ensure logo displays properly in card title section
  - Test logo integration with easter egg functionality
  - Run npm run build to implement the new changes for testing
  - _Requirements: 9.1, 9.2, 9.5_

## Phase 4: Enhancement & Optimization

- [x] 13. Implement critical resource preloading
  - Update src/frontend/src/utils/critical-css-loader.js to preload Bitcoin logos
  - Add /bitcoin-symbol.svg and /bitcoin-symbol.png to critical resources array
  - Implement preloadBitcoinLogos function with proper link rel="preload" tags
  - Ensure preloading doesn't negatively impact initial page load
  - Test preloading effectiveness and fallback behavior
  - Run npm run build to implement the new changes for testing
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 14. Add CSS animations and visual effects
  - Enhance bitcoin-logo.css with smooth transitions and hover effects
  - Implement bitcoin-logo-pulse animation for animated prop
  - Add glow effect styling for variant="glow"
  - Ensure animations respect prefers-reduced-motion accessibility setting
  - Test animation performance across different devices
  - Run npm run build to implement the new changes for testing
  - _Requirements: 7.4, 9.5_

- [x] 15. Update easter egg integration with logo URLs
  - Modify src/frontend/src/composables/useEasterEgg.js to reference Bitcoin logo URLs
  - Replace logoUrl null assignment with proper /bitcoin-symbol.svg reference
  - Ensure easter egg animations work with official Bitcoin logos
  - Test easter egg functionality with new logo system
  - Maintain accessibility and performance standards
  - Run npm run build to implement the new changes for testing
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 16. Update CSS background image utilities
  - Modify src/frontend/src/assets/css/card-layout-components.css background image references
  - Replace placeholder comments with proper url('../../../assets/bitcoin-symbol.svg') references
  - Update .nav-brand-logo and .card-bitcoin::before background images
  - Ensure CSS utilities maintain proper sizing and positioning
  - Test background image rendering across different contexts
  - Run npm run build to implement the new changes for testing
  - _Requirements: 7.2, 7.3, 7.5_

## Phase 5: Testing & Documentation

- [ ] 17. Implement comprehensive API endpoint testing
  - Create tests/api/test_bitcoin_logo_endpoints.py for backend API testing
  - Test /bitcoin-symbol.svg and /bitcoin-symbol.png endpoints for successful responses
  - Verify proper MIME types, caching headers, and ETag functionality
  - Test 404 error handling when logo files are missing
  - Add performance tests for logo serving under load
  - _Requirements: 10.2, 10.4_

- [ ] 18. Create integration tests for logo display across pages
  - Write Cypress tests in tests/e2e/logo-integration.spec.js
  - Test logo visibility and correct sizing on main application pages
  - Verify logo display in setup wizard across all steps
  - Test responsive behavior and mobile compatibility
  - Add accessibility tests for logo alt text and aria-labels
  - _Requirements: 10.3, 10.5_

- [ ] 19. Performance testing and optimization
  - Benchmark logo loading times and caching effectiveness
  - Test application performance with logo preloading enabled
  - Verify no layout shifts occur during logo loading
  - Optimize logo file sizes if needed while maintaining quality
  - Test performance across different network conditions
  - _Requirements: 8.3, 8.4, 10.5_

- [ ] 20. Final integration testing and cleanup
  - Run full application test suite to ensure no regressions
  - Verify all placeholder comments have been replaced with functional logos
  - Test logo system across all supported browsers
  - Validate accessibility compliance for all logo implementations
  - Remove any unused logo-related code or files
  - _Requirements: All requirements verification_