# Design Document

## Overview

This design document outlines the comprehensive dark theme styling system for the Bitcoin Solo Miner Monitor application. The design focuses on creating a cohesive, professional, and accessible dark theme that uses Bitcoin Orange (#F7931A) as the primary accent color throughout both the installer wizard and main application.

## Architecture

### Color System

The design implements a systematic color palette based on dark theme best practices:

**Primary Colors:**
- Bitcoin Orange: `#F7931A` (primary accent)
- Bitcoin Orange Hover: `#E58E19` (darker variant for hover states)
- Bitcoin Orange Light: `#FF9F2E` (lighter variant for subtle accents)

**Background Colors:**
- Primary Background: `#121212` (main app background)
- Surface Background: `#1E1E1E` (cards, panels, elevated surfaces)
- Secondary Surface: `#2A2A2A` (input fields, secondary panels)
- Elevated Surface: `#2C2C2C` (modals, dropdowns)

**Text Colors:**
- Primary Text: `#FFFFFF` (high emphasis text)
- Secondary Text: `#CCCCCC` (medium emphasis text)
- Disabled Text: `#666666` (low emphasis text)
- Hint Text: `#999999` (placeholder text)

**Status Colors:**
- Success: `#4CAF50` (green for positive states)
- Warning: `#FB8C00` (orange for warning states)
- Error: `#FF5252` (red for error states)
- Info: `#2196F3` (blue for informational states)

**Border and Divider Colors:**
- Primary Border: `#555555` (main borders)
- Subtle Border: `#333333` (subtle dividers)
- Focus Border: `#F7931A` (focus states)

### Typography System

**Font Stack:**
- Primary: `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`
- Fallback: `-apple-system, BlinkMacSystemFont, 'Roboto', sans-serif`

**Typography Scale:**
- H1: 32px, font-weight: 600, line-height: 1.2
- H2: 24px, font-weight: 600, line-height: 1.3
- H3: 20px, font-weight: 500, line-height: 1.4
- H4: 18px, font-weight: 500, line-height: 1.4
- Body: 16px, font-weight: 400, line-height: 1.6
- Small: 14px, font-weight: 400, line-height: 1.5
- Caption: 12px, font-weight: 400, line-height: 1.4

### Spacing System

**Base Unit:** 8px

**Spacing Scale:**
- xs: 4px (0.5 units)
- sm: 8px (1 unit)
- md: 16px (2 units)
- lg: 24px (3 units)
- xl: 32px (4 units)
- xxl: 48px (6 units)

### Elevation System

**Shadow Levels:**
- Level 1: `0 2px 4px rgba(0, 0, 0, 0.2)` (subtle elevation)
- Level 2: `0 4px 8px rgba(0, 0, 0, 0.3)` (cards, buttons)
- Level 3: `0 8px 16px rgba(0, 0, 0, 0.4)` (modals, dropdowns)
- Level 4: `0 16px 32px rgba(0, 0, 0, 0.5)` (overlays)

## Components and Interfaces

### Button System

**Primary Button:**
- Background: `#F7931A`
- Text: `#FFFFFF`
- Hover: `#E58E19`
- Focus: `#F7931A` with `0 0 0 2px rgba(247, 147, 26, 0.3)` outline
- Disabled: `#333333` background, `#666666` text

**Secondary Button:**
- Background: `transparent`
- Border: `1px solid #555555`
- Text: `#CCCCCC`
- Hover: `#2A2A2A` background
- Focus: `#F7931A` border

**Icon Button:**
- Background: `transparent`
- Text: `#CCCCCC`
- Hover: `#2A2A2A` background, `#F7931A` text
- Focus: `#F7931A` text with outline

### Form Components

**Input Fields:**
- Background: `#2A2A2A`
- Border: `1px solid #555555`
- Text: `#FFFFFF`
- Placeholder: `#999999`
- Focus: `#F7931A` border, `0 0 0 2px rgba(247, 147, 26, 0.2)` outline
- Error: `#FF5252` border

**Select Dropdowns:**
- Background: `#2C2C2C`
- Border: `1px solid #555555`
- Options: `#1E1E1E` background
- Hover: `#2A2A2A` background for options

**Checkboxes and Radio Buttons:**
- Unchecked: `transparent` background, `#555555` border
- Checked: `#F7931A` background, `#FFFFFF` checkmark
- Focus: `#F7931A` outline

### Card System

**Base Card:**
- Background: `#1E1E1E`
- Border: `1px solid #333333`
- Border-radius: `8px`
- Shadow: Level 1 elevation
- Padding: `24px`

**Elevated Card:**
- Background: `#2A2A2A`
- Shadow: Level 2 elevation
- Hover: Level 3 elevation (for interactive cards)

**Status Cards:**
- Success: `#1E1E1E` background with `#4CAF50` left border (4px)
- Warning: `#1E1E1E` background with `#FB8C00` left border (4px)
- Error: `#1E1E1E` background with `#FF5252` left border (4px)

### Navigation Components

**Sidebar Navigation:**
- Background: `#1E1E1E`
- Active Item: `#F7931A` background, `#FFFFFF` text
- Hover Item: `#2A2A2A` background
- Text: `#CCCCCC`
- Bitcoin Logo: Subtle Bitcoin logo icon next to app title

**Top Navigation:**
- Background: `#1E1E1E`
- Border-bottom: `1px solid #333333`
- Logo/Title: `#F7931A` with Bitcoin logo icon
- Bitcoin Logo: 24px Bitcoin logo in header

**Breadcrumbs:**
- Text: `#CCCCCC`
- Separator: `#666666`
- Active: `#F7931A`

### Bitcoin Logo Integration

**Logo Placement Strategy:**
- Header/Navigation: Primary Bitcoin logo (24-32px) next to application title
- Loading States: Bitcoin logo as spinner center with rotating ring
- Success States: Small Bitcoin logo (16px) in success messages
- Installer Wizard: Bitcoin logo in header and completion screen
- About Page: Large Bitcoin logo (64px) as hero element
- Favicon: Bitcoin logo as application icon

**Logo Specifications:**
- SVG format for scalability and crisp rendering
- Orange (#F7931A) and white variants
- Consistent sizing scale: 16px, 24px, 32px, 48px, 64px
- Proper alt text for accessibility

### Data Display Components

**Tables:**
- Header Background: `#2A2A2A`
- Header Text: `#FFFFFF`
- Row Background: `#1E1E1E` (odd), `#242424` (even)
- Border: `1px solid #333333`
- Hover Row: `#2A2A2A`

**Status Indicators:**
- Online: `#4CAF50` background, `#FFFFFF` text
- Offline: `#FF5252` background, `#FFFFFF` text
- Warning: `#FB8C00` background, `#FFFFFF` text
- Unknown: `#666666` background, `#CCCCCC` text

### Modal and Dialog System

**Modal Backdrop:**
- Background: `rgba(0, 0, 0, 0.7)`
- Backdrop-filter: `blur(4px)` (where supported)

**Modal Content:**
- Background: `#1E1E1E`
- Border-radius: `12px`
- Shadow: Level 4 elevation
- Max-width: `600px` (default)

**Dialog Actions:**
- Primary Action: Primary button styling
- Secondary Action: Secondary button styling
- Spacing: `16px` between buttons

## Data Models

### CSS Custom Properties Structure

```css
:root {
  /* Colors */
  --color-primary: #F7931A;
  --color-primary-hover: #E58E19;
  --color-primary-light: #FF9F2E;
  
  --color-background: #121212;
  --color-surface: #1E1E1E;
  --color-surface-secondary: #2A2A2A;
  --color-surface-elevated: #2C2C2C;
  
  --color-text-primary: #FFFFFF;
  --color-text-secondary: #CCCCCC;
  --color-text-disabled: #666666;
  --color-text-hint: #999999;
  
  --color-border: #555555;
  --color-border-subtle: #333333;
  --color-border-focus: #F7931A;
  
  --color-success: #4CAF50;
  --color-warning: #FB8C00;
  --color-error: #FF5252;
  --color-info: #2196F3;
  
  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-xxl: 48px;
  
  /* Typography */
  --font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  --font-size-h1: 32px;
  --font-size-h2: 24px;
  --font-size-h3: 20px;
  --font-size-h4: 18px;
  --font-size-body: 16px;
  --font-size-small: 14px;
  --font-size-caption: 12px;
  
  /* Elevation */
  --shadow-1: 0 2px 4px rgba(0, 0, 0, 0.2);
  --shadow-2: 0 4px 8px rgba(0, 0, 0, 0.3);
  --shadow-3: 0 8px 16px rgba(0, 0, 0, 0.4);
  --shadow-4: 0 16px 32px rgba(0, 0, 0, 0.5);
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.5s ease;
}
```

### Vuetify Theme Configuration

```javascript
const vuetifyTheme = {
  defaultTheme: 'dark',
  themes: {
    dark: {
      dark: true,
      colors: {
        primary: '#F7931A',
        secondary: '#424242',
        accent: '#FF9F2E',
        error: '#FF5252',
        info: '#2196F3',
        success: '#4CAF50',
        warning: '#FB8C00',
        background: '#121212',
        surface: '#1E1E1E',
        'surface-variant': '#2A2A2A',
        'on-surface': '#FFFFFF',
        'on-surface-variant': '#CCCCCC',
        'on-primary': '#FFFFFF',
      }
    }
  }
}
```

## Error Handling

### CSS Fallbacks

**Color Fallbacks:**
- If CSS custom properties aren't supported, provide fallback colors
- Use `@supports` queries for advanced features like backdrop-filter
- Ensure graceful degradation for older browsers

**Font Fallbacks:**
- Comprehensive font stack with system fonts as fallbacks
- Web-safe fonts as final fallback
- Font loading optimization to prevent FOUT (Flash of Unstyled Text)

**Animation Fallbacks:**
- Respect `prefers-reduced-motion` media query
- Provide instant state changes for users who prefer reduced motion
- Ensure functionality works without animations

### Accessibility Error Prevention

**Contrast Validation:**
- All color combinations must meet WCAG 2.1 AA standards
- Automated testing for contrast ratios
- Manual verification for edge cases

**Focus Management:**
- Visible focus indicators for all interactive elements
- Logical tab order throughout the application
- Skip links for keyboard navigation

**Colorblind Accessibility:**
- Animation-based indicators for state changes (pulse, fade, slide)
- Icon-based status indicators alongside color coding
- Pattern/texture variations for different states
- Motion cues for important state transitions

### Animation System for Accessibility

**State Change Animations:**
- Success states: Gentle pulse animation with checkmark icon
- Error states: Subtle shake animation with warning icon
- Loading states: Smooth rotation with progress indication
- Focus states: Gentle glow animation around focused elements

**Colorblind-Friendly Indicators:**
- Online status: Green color + upward arrow animation + checkmark icon
- Offline status: Red color + downward arrow animation + X icon
- Warning status: Orange color + pulse animation + warning triangle icon
- Processing status: Blue color + rotation animation + spinner icon

## Testing Strategy

### Visual Regression Testing

**Screenshot Comparison:**
- Automated screenshots of key components in different states
- Cross-browser testing for styling consistency
- Mobile and desktop viewport testing

**Component Testing:**
- Individual component styling verification
- State-based testing (hover, focus, active, disabled)
- Theme switching validation

### Accessibility Testing

**Automated Testing:**
- axe-core integration for accessibility rule checking
- Color contrast ratio validation
- Keyboard navigation testing

**Manual Testing:**
- Screen reader compatibility testing
- High contrast mode verification
- Zoom level testing (up to 200%)

### Performance Testing

**CSS Performance:**
- Bundle size analysis for CSS files
- Critical CSS identification and inlining
- Unused CSS detection and removal

**Runtime Performance:**
- Animation performance profiling
- Paint and layout thrashing detection
- Memory usage monitoring for CSS-in-JS solutions

### Cross-Browser Testing

**Browser Support Matrix:**
- Chrome 90+ (primary target)
- Firefox 88+ (secondary target)
- Safari 14+ (secondary target)
- Edge 90+ (secondary target)

**Feature Testing:**
- CSS Grid and Flexbox support
- CSS Custom Properties support
- Modern CSS features (backdrop-filter, etc.)

### Integration Testing

**Theme Consistency:**
- Installer wizard to main app transition
- Component integration within themed environment
- State persistence across page reloads

**Responsive Testing:**
- Breakpoint behavior validation
- Touch interaction testing on mobile devices
- Orientation change handling

**Regression Testing Strategy:**
- Automated visual regression tests for all styled components
- Unit tests for CSS utility functions and theme switching
- Integration tests for installer wizard styling
- End-to-end tests covering complete user flows with new styling
- Performance benchmarks to ensure styling changes don't impact load times

### Easter Egg Feature: Secret Animation

**Subtle Implementation:**
- Key sequence: Cryptographically hashed for security
- Trigger: Global keyboard event listener with hash verification
- Animation: Raining Bitcoin logos from top of screen
- Duration: 5 seconds with fade-out
- Logos: 20-30 Bitcoin logos falling at different speeds
- Physics: Realistic gravity and bounce effects
- Sound: Optional Bitcoin "cha-ching" sound effect (muted by default)
- Cleanup: Automatic removal after animation completes
- Accessibility: Respects prefers-reduced-motion setting

**Cryptic Hints Strategy:**
- Minimal console message: "₿ Some secrets are earned... 🎮"
- Subtle code comments: "1986... some things never change" and "↑↑↓↓ is just the beginning"
- Variable names: `LEGACY_HASH`, `CLASSIC_PATTERN_LENGTH = 11`
- UI hints: Small "🎮" icon in footer, "Est. 1986" reference
- Documentation: "Patterns from gaming's golden age still hold power"

**Animation Specifications:**
- Logo size: 32px Bitcoin logos in orange (#F7931A)
- Fall speed: Randomized between 2-5 seconds per logo
- Horizontal spread: Random X positions across viewport width
- Rotation: Gentle rotation during fall (0-360 degrees)
- Z-index: High value (9999) to appear above all content
- Performance: Hardware-accelerated transforms (translate3d, rotate3d)
- Mobile: Touch-friendly alternative trigger (tap sequence on logo)