# Card & Layout Components

This document describes the enhanced card system, navigation components, data tables, and status indicators implemented for the Bitcoin Solo Miner Monitor application.

## Overview

The card and layout components provide a comprehensive system for building consistent, accessible, and visually appealing interfaces with Bitcoin Orange theming and professional dark mode styling.

## Components

### 1. Card System

#### Base Card Component
```css
.card-component
```
The foundational card class with proper elevation, padding, and border radius.

#### Elevation Levels
- `.card-flat` - No shadow, subtle border only
- `.card-elevated-1` - Basic shadow (Level 1)
- `.card-elevated-2` - Medium shadow with elevated surface (Level 2)
- `.card-elevated-3` - Higher shadow for prominent elements (Level 3)
- `.card-elevated-4` - Maximum shadow for overlays (Level 4)

#### Interactive Cards
```css
.card-interactive
```
Adds hover effects with transform and shadow animations.

#### Card Variants
- `.card-primary` - Bitcoin Orange left border accent
- `.card-success` - Green left border accent
- `.card-warning` - Orange left border accent
- `.card-error` - Red left border accent
- `.card-info` - Blue left border accent
- `.card-bitcoin` - Bitcoin logo watermark with hover effects

#### Card Structure
```html
<div class="card-component card-elevated-2 card-interactive">
  <div class="card-header">
    <h4 class="card-title">Card Title</h4>
    <div class="card-subtitle">Optional subtitle</div>
  </div>
  <div class="card-content">
    <!-- Card content -->
  </div>
  <div class="card-actions card-actions-between">
    <button class="btn btn-secondary">Cancel</button>
    <button class="btn btn-primary">Confirm</button>
  </div>
</div>
```

#### Card Grid System
- `.card-grid` - Responsive grid (300px minimum)
- `.card-grid-2` - 2-column responsive grid (250px minimum)
- `.card-grid-3` - 3-column responsive grid (200px minimum)
- `.card-grid-4` - 4-column responsive grid (180px minimum)

### 2. Navigation Components

#### Sidebar Navigation
```css
.nav-sidebar
```
Fixed sidebar with Bitcoin logo integration and smooth transitions.

#### Navigation Brand
```html
<div class="nav-brand">
  <div class="nav-brand-logo"></div>
  <div>
    <div class="nav-brand-text">Bitcoin Solo Miner Monitor</div>
    <div class="nav-brand-subtitle">Monitor your mining fleet</div>
  </div>
</div>
```

#### Navigation Items
```html
<a href="#" class="nav-item active">
  <div class="nav-item-icon">📊</div>
  <div class="nav-item-text">Dashboard</div>
  <div class="nav-item-badge">3</div>
</a>
```

#### Top Navigation Bar
```css
.nav-topbar
```
Fixed top bar that adjusts based on sidebar state.

### 3. Data Table Components

#### Enhanced Data Table
```html
<table class="data-table">
  <thead>
    <tr>
      <th class="sortable sorted-desc">Name</th>
      <th class="sortable numeric">Hashrate</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr class="selected">
      <td>Miner Name</td>
      <td class="numeric">1.2 TH/s</td>
      <td class="actions">
        <button class="btn btn-ghost btn-small">View</button>
      </td>
    </tr>
  </tbody>
</table>
```

#### Table Features
- Alternating row colors with hover effects
- Sortable headers with visual indicators
- Selected row highlighting
- Responsive design with proper spacing
- Loading and empty states

### 4. Status Indicator Components

#### Basic Status Indicators
```html
<div class="status-indicator status-online">
  <div class="status-indicator-icon online"></div>
  Online
</div>
```

#### Status Variants
- `.status-online` - Green with pulsing animation
- `.status-offline` - Red, static
- `.status-warning` - Orange with blinking animation
- `.status-info` - Blue, static
- `.status-unknown` - Gray, static

#### Large Status Indicators
```css
.status-indicator-lg
```
Larger version for prominent status displays.

#### Status Badges
```html
<div style="position: relative;">
  <div class="status-badge online"></div>
  <!-- Content with status badge -->
</div>
```

## Animations and Accessibility

### Animations
- **Status Pulse**: Smooth pulsing for online/active states
- **Status Blink**: Attention-grabbing blink for warnings
- **Card Hover**: Lift effect with shadow enhancement
- **Logo Hover**: Subtle scale animation for Bitcoin logos

### Accessibility Features
- **Reduced Motion**: All animations respect `prefers-reduced-motion`
- **High Contrast**: Enhanced borders and contrast in high contrast mode
- **Focus Management**: Proper focus indicators for keyboard navigation
- **Screen Reader Support**: Semantic HTML and ARIA labels
- **Color Independence**: Icons and animations supplement color coding

## Responsive Design

### Breakpoints
- **Desktop**: Full layout with sidebar (1024px+)
- **Tablet**: Collapsible sidebar (768px - 1024px)
- **Mobile**: Hidden sidebar, stacked cards (< 768px)
- **Small Mobile**: Single column layout (< 480px)

### Mobile Adaptations
- Cards stack in single column
- Table text size reduces
- Navigation becomes overlay
- Touch-friendly button sizes
- Simplified animations

## Bitcoin Branding Integration

### Logo Integration
- Navigation brand with Bitcoin logo
- Card watermarks with hover effects
- Status indicators with Bitcoin context
- Button integration with logo icons

### Color Scheme
- **Primary**: Bitcoin Orange (#F7931A)
- **Hover**: Darker Bitcoin Orange (#E58E19)
- **Light**: Lighter Bitcoin Orange (#FF9F2E)
- **Backgrounds**: Professional dark theme
- **Status Colors**: Accessible contrast ratios

## Usage Examples

### Miner Status Card
```html
<div class="card-component card-bitcoin card-interactive card-elevated-2">
  <div class="card-header">
    <h4 class="card-title">
      <BitcoinLogo :size="24" />
      Bitaxe Ultra #1
    </h4>
    <div class="status-indicator status-online">
      <div class="status-indicator-icon online"></div>
      Mining
    </div>
  </div>
  <div class="card-content">
    <div class="d-flex justify-between">
      <div>
        <div class="text-small text-secondary">Hashrate</div>
        <div class="text-h4 text-bitcoin">1.2 TH/s</div>
      </div>
      <div>
        <div class="text-small text-secondary">Temperature</div>
        <div class="text-h4">65°C</div>
      </div>
    </div>
  </div>
  <div class="card-actions card-actions-between">
    <button class="btn btn-secondary">Details</button>
    <button class="btn-bitcoin">
      <BitcoinLogo :size="16" />
      Restart
    </button>
  </div>
</div>
```

### Dashboard Grid
```html
<div class="card-grid card-grid-3">
  <div class="card-component card-primary">
    <!-- Summary card -->
  </div>
  <div class="card-component card-success">
    <!-- Performance card -->
  </div>
  <div class="card-component card-warning">
    <!-- Alerts card -->
  </div>
</div>
```

### Status Dashboard
```html
<div class="status-grid">
  <div class="status-indicator status-indicator-lg status-online">
    <div class="status-indicator-icon online"></div>
    API Server
  </div>
  <div class="status-indicator status-indicator-lg status-warning">
    <div class="status-indicator-icon warning"></div>
    Database
  </div>
</div>
```

## Testing

### Test Files
- `card-layout-test.html` - Standalone HTML test
- `CardLayoutTest.vue` - Vue component test
- `CardLayoutDemo.vue` - Reusable demo component

### Test Coverage
- All card elevation levels
- Interactive hover effects
- Status indicator animations
- Navigation components
- Data table functionality
- Responsive behavior
- Accessibility features

### Browser Testing
- Chrome 90+ (primary)
- Firefox 88+ (secondary)
- Safari 14+ (secondary)
- Edge 90+ (secondary)

## Performance Considerations

### Optimizations
- Hardware-accelerated transforms
- Efficient CSS selectors
- Minimal repaints and reflows
- Optimized animation timing
- Reduced motion support

### Bundle Size
- Modular CSS architecture
- Utility class system
- Minimal redundancy
- Tree-shakeable components

## Future Enhancements

### Planned Features
- Additional card variants
- More status indicator types
- Enhanced table features
- Advanced navigation patterns
- Theme customization options

### Accessibility Improvements
- Enhanced screen reader support
- Better keyboard navigation
- Voice control compatibility
- Improved color contrast options

## Dependencies

### Required Files
- `variables.css` - CSS custom properties
- `utilities.css` - Utility classes
- `bitcoin-components.css` - Bitcoin branding
- Bitcoin logo SVG assets

### Optional Integrations
- Vuetify theme system
- Vue.js components
- Animation libraries
- Icon systems