# Bitcoin Logo Reimplementation Design

## Overview

This design document outlines the architecture and implementation approach for reimplementing the Bitcoin logo system using the official Bitcoin symbols. The design prioritizes simplicity, performance, and maintainability while ensuring consistent branding across the application.

## Architecture

### Component Architecture

```
BitcoinLogo.vue (Core Component)
├── Props: size, variant, animated, ariaLabel
├── Computed: logoSrc, logoSize, componentClasses
├── Template: <img> with dynamic src and styling
└── Styles: Responsive sizing and animations

Backend API Service
├── /bitcoin-symbol.svg endpoint
├── /bitcoin-symbol.png endpoint  
├── Proper MIME types and caching
└── Error handling for missing files

CSS Utilities
├── .bitcoin-logo-* size classes
├── Background image utilities
├── Animation and transition styles
└── Responsive design support
```

### File Structure

```
assets/
├── bitcoin-symbol.svg (Official SVG logo)
└── bitcoin-symbol.png (Official PNG logo)

src/frontend/src/components/
├── BitcoinLogo.vue (New core component)
├── BitcoinLoadingSpinner.vue (Updated)
└── BitcoinSuccessMessage.vue (Updated)

src/frontend/src/assets/css/
├── bitcoin-logo.css (New logo-specific styles)
└── main.css (Updated imports)

src/backend/api/
└── api_service.py (Updated endpoints)
```

## Components and Interfaces

### BitcoinLogo Component Interface

```vue
<template>
  <img
    :src="logoSrc"
    :alt="altText"
    :aria-label="ariaLabel"
    :class="componentClasses"
    :style="componentStyles"
    @load="onLogoLoad"
    @error="onLogoError"
  />
</template>

<script>
export default {
  name: 'BitcoinLogo',
  props: {
    // Size in pixels or preset ('sm', 'md', 'lg', 'xl', 'hero')
    size: {
      type: [Number, String],
      default: 'md',
      validator: (value) => {
        if (typeof value === 'number') return value > 0 && value <= 256
        return ['xs', 'sm', 'md', 'lg', 'xl', 'hero'].includes(value)
      }
    },
    
    // Visual variant ('default', 'glow', 'subtle')
    variant: {
      type: String,
      default: 'default',
      validator: (value) => ['default', 'glow', 'subtle'].includes(value)
    },
    
    // Animation support
    animated: {
      type: Boolean,
      default: false
    },
    
    // Accessibility
    ariaLabel: {
      type: String,
      default: 'Bitcoin Logo'
    },
    
    // Custom alt text
    altText: {
      type: String,
      default: 'Bitcoin'
    }
  }
}
</script>
```

### Size Mapping System

```javascript
const SIZE_MAP = {
  xs: 16,
  sm: 24, 
  md: 32,
  lg: 48,
  xl: 64,
  hero: 96
}

const logoSrc = computed(() => {
  const pixelSize = typeof props.size === 'number' ? props.size : SIZE_MAP[props.size]
  
  // Use SVG for smaller sizes (crisp rendering)
  // Use PNG for larger sizes (better quality)
  return pixelSize <= 32 ? '/bitcoin-symbol.svg' : '/bitcoin-symbol.png'
})
```

### Backend API Design

```python
# Enhanced API endpoints with proper caching and error handling
@self.app.get("/bitcoin-symbol.svg")
async def bitcoin_symbol_svg():
    bitcoin_svg_path = app_paths.base_path / "assets" / "bitcoin-symbol.svg"
    if bitcoin_svg_path.exists():
        return FileResponse(
            str(bitcoin_svg_path), 
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=31536000",  # 1 year
                "ETag": f'"{bitcoin_svg_path.stat().st_mtime}"'
            }
        )
    raise HTTPException(status_code=404, detail="Bitcoin symbol SVG not found")

@self.app.get("/bitcoin-symbol.png") 
async def bitcoin_symbol_png():
    bitcoin_png_path = app_paths.base_path / "assets" / "bitcoin-symbol.png"
    if bitcoin_png_path.exists():
        return FileResponse(
            str(bitcoin_png_path),
            media_type="image/png", 
            headers={
                "Cache-Control": "public, max-age=31536000",  # 1 year
                "ETag": f'"{bitcoin_png_path.stat().st_mtime}"'
            }
        )
    raise HTTPException(status_code=404, detail="Bitcoin symbol PNG not found")
```

## Data Models

### Logo Configuration Model

```javascript
// Logo configuration for different contexts
const LOGO_CONTEXTS = {
  appBar: {
    size: 'sm',
    variant: 'default',
    animated: false
  },
  
  navigationDrawer: {
    size: 'md', 
    variant: 'default',
    animated: false
  },
  
  wizardHeader: {
    size: 'lg',
    variant: 'glow',
    animated: true
  },
  
  welcomeHero: {
    size: 'hero',
    variant: 'glow', 
    animated: true
  },
  
  aboutHero: {
    size: 'xl',
    variant: 'default',
    animated: false
  },
  
  loadingSpinner: {
    size: 'md',
    variant: 'default',
    animated: false
  },
  
  successMessage: {
    size: 'sm',
    variant: 'glow',
    animated: true
  }
}
```

### CSS Class System

```css
/* Base logo styles */
.bitcoin-logo {
  display: inline-block;
  max-width: 100%;
  height: auto;
  transition: all 0.3s ease;
}

/* Size variants */
.bitcoin-logo--xs { width: 16px; height: 16px; }
.bitcoin-logo--sm { width: 24px; height: 24px; }
.bitcoin-logo--md { width: 32px; height: 32px; }
.bitcoin-logo--lg { width: 48px; height: 48px; }
.bitcoin-logo--xl { width: 64px; height: 64px; }
.bitcoin-logo--hero { width: 96px; height: 96px; }

/* Visual variants */
.bitcoin-logo--glow {
  filter: drop-shadow(0 0 8px rgba(247, 147, 26, 0.4));
}

.bitcoin-logo--subtle {
  opacity: 0.8;
}

/* Animation support */
.bitcoin-logo--animated {
  animation: bitcoin-logo-pulse 2s ease-in-out infinite;
}

@keyframes bitcoin-logo-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

/* Responsive design */
@media (max-width: 768px) {
  .bitcoin-logo--hero { width: 64px; height: 64px; }
  .bitcoin-logo--xl { width: 48px; height: 48px; }
}
```

## Error Handling

### Component Error Handling

```javascript
// BitcoinLogo.vue error handling
const logoError = ref(false)
const logoLoaded = ref(false)

const onLogoError = () => {
  logoError.value = true
  console.warn('Bitcoin logo failed to load:', logoSrc.value)
  // Emit error event for parent components to handle
  emit('logo-error', { src: logoSrc.value })
}

const onLogoLoad = () => {
  logoLoaded.value = true
  logoError.value = false
  emit('logo-loaded', { src: logoSrc.value })
}

// Fallback rendering
const showFallback = computed(() => logoError.value)
```

### API Error Handling

```python
# Comprehensive error handling for logo endpoints
async def serve_bitcoin_logo(file_path: Path, media_type: str):
    try:
        if not file_path.exists():
            logger.warning(f"Bitcoin logo file not found: {file_path}")
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "Logo file not found",
                    "file": str(file_path.name),
                    "suggestion": "Ensure Bitcoin logo files are present in assets/ directory"
                }
            )
        
        # Check file permissions
        if not os.access(file_path, os.R_OK):
            logger.error(f"Cannot read Bitcoin logo file: {file_path}")
            raise HTTPException(
                status_code=403,
                detail="Logo file access denied"
            )
            
        return FileResponse(str(file_path), media_type=media_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving Bitcoin logo: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error serving logo"
        )
```

## Testing Strategy

### Component Testing

```javascript
// BitcoinLogo.test.js
describe('BitcoinLogo Component', () => {
  test('renders with correct size prop', () => {
    const wrapper = mount(BitcoinLogo, {
      props: { size: 'lg' }
    })
    expect(wrapper.find('img').classes()).toContain('bitcoin-logo--lg')
  })
  
  test('uses SVG for small sizes', () => {
    const wrapper = mount(BitcoinLogo, {
      props: { size: 24 }
    })
    expect(wrapper.find('img').attributes('src')).toBe('/bitcoin-symbol.svg')
  })
  
  test('uses PNG for large sizes', () => {
    const wrapper = mount(BitcoinLogo, {
      props: { size: 64 }
    })
    expect(wrapper.find('img').attributes('src')).toBe('/bitcoin-symbol.png')
  })
  
  test('handles load errors gracefully', async () => {
    const wrapper = mount(BitcoinLogo)
    await wrapper.find('img').trigger('error')
    expect(wrapper.emitted('logo-error')).toBeTruthy()
  })
})
```

### API Testing

```python
# test_bitcoin_logo_api.py
async def test_bitcoin_symbol_svg_endpoint():
    response = await client.get("/bitcoin-symbol.svg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "Cache-Control" in response.headers

async def test_bitcoin_symbol_png_endpoint():
    response = await client.get("/bitcoin-symbol.png") 
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

async def test_missing_logo_file():
    # Test when logo file is missing
    response = await client.get("/bitcoin-symbol.svg")
    if response.status_code == 404:
        assert "not found" in response.json()["detail"].lower()
```

### Integration Testing

```javascript
// Integration tests for logo display across pages
describe('Logo Integration', () => {
  test('displays logo in app header', () => {
    cy.visit('/')
    cy.get('[data-testid="app-header-logo"]').should('be.visible')
    cy.get('[data-testid="app-header-logo"] img').should('have.attr', 'src')
  })
  
  test('displays logo in setup wizard', () => {
    cy.visit('/setup')
    cy.get('[data-testid="wizard-header-logo"]').should('be.visible')
  })
  
  test('displays hero logo on about page', () => {
    cy.visit('/about')
    cy.get('[data-testid="about-hero-logo"]').should('be.visible')
  })
})
```

## Performance Considerations

### Resource Optimization

```javascript
// Critical resource preloading
const preloadBitcoinLogos = () => {
  const criticalLogos = [
    '/bitcoin-symbol.svg',  // Most commonly used
    '/bitcoin-symbol.png'   // For larger displays
  ]
  
  criticalLogos.forEach(logoUrl => {
    const link = document.createElement('link')
    link.rel = 'preload'
    link.as = 'image'
    link.href = logoUrl
    document.head.appendChild(link)
  })
}
```

### Lazy Loading Strategy

```javascript
// Lazy loading for non-critical logos
const useLazyLogo = (size) => {
  const logoRef = ref(null)
  const isVisible = ref(false)
  
  onMounted(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        isVisible.value = true
        observer.disconnect()
      }
    })
    
    if (logoRef.value) {
      observer.observe(logoRef.value)
    }
  })
  
  return { logoRef, isVisible }
}
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create BitcoinLogo.vue component
2. Implement backend API endpoints
3. Add basic CSS utilities
4. Set up component testing

### Phase 2: Application Integration  
1. Integrate logos in App.vue (header/navigation)
2. Update FirstRunWizard.vue
3. Update WelcomeScreen.vue and NetworkDiscoveryScreen.vue
4. Test wizard integration

### Phase 3: Page Integration
1. Update About.vue hero section
2. Update BitcoinLoadingSpinner.vue
3. Update BitcoinSuccessMessage.vue
4. Test component integration

### Phase 4: Enhancement & Optimization
1. Implement critical resource preloading
2. Add CSS animations and transitions
3. Update easter egg integration
4. Performance testing and optimization

### Phase 5: Testing & Documentation
1. Comprehensive integration testing
2. Cross-browser compatibility testing
3. Performance benchmarking
4. Documentation updates

This design provides a solid foundation for implementing a clean, maintainable Bitcoin logo system that uses only the official Bitcoin symbols while maintaining excellent performance and user experience.