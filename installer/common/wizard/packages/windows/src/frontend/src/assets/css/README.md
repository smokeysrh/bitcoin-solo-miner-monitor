# Bitcoin Solo Miner Monitor - CSS System Documentation

## Overview

This CSS system provides a comprehensive, professional dark theme with Bitcoin Orange accents for the Bitcoin Solo Miner Monitor application. The system is built with accessibility, performance, and maintainability in mind.

## Architecture

### File Structure

```
src/assets/css/
├── main.css              # Main entry point, imports all other CSS files
├── variables.css         # CSS custom properties and design tokens
├── utilities.css         # Utility classes for spacing, typography, etc.
├── bitcoin-components.css # Bitcoin-specific components and logo utilities
└── README.md            # This documentation file

src/assets/images/
├── bitcoin-logo.svg         # Main Bitcoin logo (64px)
├── bitcoin-logo-16.svg      # Small Bitcoin logo (16px)
├── bitcoin-logo-24.svg      # Medium Bitcoin logo (24px)
├── bitcoin-logo-32.svg      # Large Bitcoin logo (32px)
├── bitcoin-logo-48.svg      # Extra large Bitcoin logo (48px)
├── bitcoin-logo-white.svg   # White variant for dark backgrounds
└── bitcoin-favicon.svg      # Favicon version
```

## Design System

### Color Palette

#### Primary Colors
- **Bitcoin Orange**: `#F7931A` - Primary accent color
- **Bitcoin Orange Hover**: `#E58E19` - Darker variant for hover states
- **Bitcoin Orange Light**: `#FF9F2E` - Lighter variant for subtle accents

#### Background Colors
- **Primary Background**: `#121212` - Main app background
- **Surface Background**: `#1E1E1E` - Cards, panels, elevated surfaces
- **Secondary Surface**: `#2A2A2A` - Input fields, secondary panels
- **Elevated Surface**: `#2C2C2C` - Modals, dropdowns

#### Text Colors
- **Primary Text**: `#FFFFFF` - High emphasis text
- **Secondary Text**: `#CCCCCC` - Medium emphasis text
- **Disabled Text**: `#666666` - Low emphasis text
- **Hint Text**: `#999999` - Placeholder text

#### Status Colors
- **Success**: `#4CAF50` - Green for positive states
- **Warning**: `#FB8C00` - Orange for warning states
- **Error**: `#FF5252` - Red for error states
- **Info**: `#2196F3` - Blue for informational states

### Typography

#### Font Stack
- Primary: `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`
- Monospace: `'Consolas', 'Monaco', 'Courier New', monospace`

#### Typography Scale
- **H1**: 32px, font-weight: 600, line-height: 1.2
- **H2**: 24px, font-weight: 600, line-height: 1.3
- **H3**: 20px, font-weight: 500, line-height: 1.4
- **H4**: 18px, font-weight: 500, line-height: 1.4
- **Body**: 16px, font-weight: 400, line-height: 1.6
- **Small**: 14px, font-weight: 400, line-height: 1.5
- **Caption**: 12px, font-weight: 400, line-height: 1.4

### Spacing System

Based on an 8px grid system:
- **XS**: 4px (0.5 units)
- **SM**: 8px (1 unit)
- **MD**: 16px (2 units)
- **LG**: 24px (3 units)
- **XL**: 32px (4 units)
- **XXL**: 48px (6 units)

### Elevation System

Box shadow levels for depth:
- **Level 1**: `0 2px 4px rgba(0, 0, 0, 0.2)` - Subtle elevation
- **Level 2**: `0 4px 8px rgba(0, 0, 0, 0.3)` - Cards, buttons
- **Level 3**: `0 8px 16px rgba(0, 0, 0, 0.4)` - Modals, dropdowns
- **Level 4**: `0 16px 32px rgba(0, 0, 0, 0.5)` - Overlays

## Usage

### CSS Custom Properties

All design tokens are available as CSS custom properties:

```css
.my-component {
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1);
}
```

### Utility Classes

#### Spacing
```html
<!-- Margin -->
<div class="m-md">Margin medium</div>
<div class="mt-lg">Margin top large</div>
<div class="mx-sm">Margin horizontal small</div>

<!-- Padding -->
<div class="p-lg">Padding large</div>
<div class="py-md">Padding vertical medium</div>
```

#### Typography
```html
<h1 class="text-h1">Heading 1</h1>
<p class="text-body text-secondary">Secondary body text</p>
<span class="text-small text-bitcoin">Bitcoin orange text</span>
```

#### Layout
```html
<div class="d-flex justify-center align-center">
  <span>Centered content</span>
</div>
```

#### Colors
```html
<div class="bg-surface text-primary">Surface background</div>
<button class="bg-primary text-on-primary">Primary button</button>
```

### Bitcoin Logo Components

#### Basic Logo
```html
<!-- Use the BitcoinLogo component instead -->
<BitcoinLogo :size="16" />
<BitcoinLogo :size="24" />
<BitcoinLogo :size="32" />
```

#### Brand Component
```html
<div class="bitcoin-brand">
  <BitcoinLogo :size="24" />
  <span>Bitcoin Solo Miner Monitor</span>
</div>
```

#### Loading Spinner
```html
<div class="bitcoin-loading-spinner"></div>
<div class="bitcoin-loading-spinner bitcoin-loading-spinner-sm"></div>
<div class="bitcoin-loading-spinner bitcoin-loading-spinner-lg"></div>
```

#### Status Indicators
```html
<div class="bitcoin-status bitcoin-status-online">
  <BitcoinLogo :size="12" />
  Online
</div>
```

#### Bitcoin Button
```html
<button class="btn-bitcoin">
  <BitcoinLogo :size="16" />
  Bitcoin Action
</button>
```

### Component Examples

#### Card Component
```html
<div class="card">
  <h3 class="text-h3 mb-md">Card Title</h3>
  <p class="text-body text-secondary">Card content goes here.</p>
</div>
```

#### Button Components
```html
<button class="btn btn-primary">Primary Button</button>
<button class="btn btn-secondary">Secondary Button</button>
<button class="btn btn-ghost">Ghost Button</button>
```

#### Input Components
```html
<input type="text" class="input" placeholder="Enter text...">
```

#### Status Indicators
```html
<span class="status-indicator status-online">Online</span>
<span class="status-indicator status-offline">Offline</span>
<span class="status-indicator status-warning">Warning</span>
```

## Accessibility Features

### Color Contrast
- All color combinations meet WCAG 2.1 AA contrast requirements
- High contrast mode support with enhanced borders and text

### Motion Preferences
- Respects `prefers-reduced-motion` setting
- Animations are disabled or simplified for users who prefer reduced motion

### Focus Management
- Clear focus indicators for all interactive elements
- Keyboard navigation support
- Skip links for screen readers

### Screen Reader Support
- Semantic HTML structure
- Proper ARIA labels where needed
- Alternative text for logo images

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance Considerations

- CSS custom properties for efficient theming
- Minimal CSS bundle size through utility-first approach
- Hardware-accelerated animations using `transform` and `opacity`
- Critical CSS inlining for faster initial paint

## Integration with Vuetify

The CSS system is designed to work alongside Vuetify. The main.js file includes enhanced Vuetify theme configuration:

```javascript
theme: {
  defaultTheme: "dark",
  themes: {
    dark: {
      colors: {
        primary: "#F7931A",
        "primary-darken-1": "#E58E19",
        "primary-lighten-1": "#FF9F2E",
        // ... additional color variants
      }
    }
  }
}
```

## Customization

### Adding New Colors
1. Add the color to `variables.css`:
```css
:root {
  --color-custom: #YOUR_COLOR;
}
```

2. Add utility classes in `utilities.css`:
```css
.text-custom { color: var(--color-custom); }
.bg-custom { background-color: var(--color-custom); }
```

### Adding New Components
1. Create component styles in `bitcoin-components.css`
2. Follow the existing naming conventions
3. Include responsive variants if needed
4. Add accessibility considerations

### Modifying Spacing
Update the spacing scale in `variables.css`:
```css
:root {
  --spacing-new-size: 20px;
}
```

Then add utility classes in `utilities.css`.

## Testing

A test HTML file is included at `src/assets/css/test.html` to verify the CSS system works correctly. Open this file in a browser to see all components and utilities in action.

## Maintenance

### Regular Tasks
- Validate color contrast ratios when adding new colors
- Test with screen readers when adding new components
- Verify responsive behavior on different screen sizes
- Check performance impact of new animations

### Updates
- Keep design tokens in sync with design system
- Update documentation when adding new components
- Maintain browser compatibility matrix
- Regular accessibility audits

## Future Enhancements

- Light theme support (foundation already in place)
- Additional Bitcoin-themed animations
- More comprehensive component library
- CSS-in-JS integration options
- Advanced theming capabilities