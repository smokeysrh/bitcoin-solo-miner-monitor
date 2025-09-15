# Frontend Testing Documentation

## Overview

This directory contains unit tests for Vue components using Vitest and Vue Test Utils.

## Setup

The testing framework is configured with:
- **Vitest**: Fast unit test runner
- **Vue Test Utils**: Official testing utilities for Vue.js
- **jsdom**: DOM environment for testing
- **@vitest/ui**: Optional UI for test visualization

## Running Tests

### All Tests
```bash
npm run test
```

### Specific Test File
```bash
npx vitest run tests/unit/components/BitcoinLogo.test.js
```

### Watch Mode
```bash
npm run test
```

### Test UI
```bash
npm run test:ui
```

### Coverage Report
```bash
npm run test:coverage
```

## Test Structure

### BitcoinLogo Component Tests

Located at: `tests/unit/components/BitcoinLogo.test.js`

**Test Coverage:**
- ✅ Default rendering with proper props
- ✅ Size prop validation (string presets and numeric values)
- ✅ SVG vs PNG selection logic based on size (≤32px uses SVG, >32px uses PNG)
- ✅ CSS class application for size variants
- ✅ Variant prop validation (default, glow, subtle)
- ✅ Animation support
- ✅ Accessibility attributes (aria-label, alt text)
- ✅ Error handling (onLogoError, onLogoLoad events)
- ✅ Event emission testing
- ✅ Complex prop combinations
- ✅ Edge cases and boundary conditions

**Requirements Covered:**
- Requirement 10.1: Component unit testing with Vue Test Utils
- Requirement 10.4: Comprehensive test coverage for all component functionality

## Configuration Files

- `vitest.config.js`: Main Vitest configuration
- `tests/setup.js`: Global test setup and mocks
- `package.json`: Test scripts and dependencies

## Adding New Tests

1. Create test files in the appropriate subdirectory under `tests/`
2. Follow the naming convention: `ComponentName.test.js`
3. Import required testing utilities:
   ```javascript
   import { describe, it, expect, vi, beforeEach } from 'vitest'
   import { mount } from '@vue/test-utils'
   ```
4. Use the `@/` alias for component imports
5. Group related tests using `describe` blocks
6. Use descriptive test names with `it` or `test`

## Best Practices

- Test behavior, not implementation details
- Use meaningful test descriptions
- Mock external dependencies
- Test edge cases and error conditions
- Maintain good test coverage
- Keep tests focused and isolated