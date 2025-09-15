/**
 * BitcoinLogo Component Unit Tests
 * Tests for the BitcoinLogo Vue component functionality
 * Requirements: 10.1, 10.4
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BitcoinLogo from '@/components/BitcoinLogo.vue'

describe('BitcoinLogo Component', () => {
  let wrapper

  beforeEach(() => {
    // Reset any mocks before each test
    vi.clearAllMocks()
  })

  describe('Default Rendering', () => {
    it('should render with default props', () => {
      wrapper = mount(BitcoinLogo)
      
      const img = wrapper.find('img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('/bitcoin-symbol.svg') // md size (32px) uses SVG
      expect(img.attributes('alt')).toBe('Bitcoin')
      expect(img.attributes('aria-label')).toBe('Bitcoin Logo')
      expect(img.classes()).toContain('bitcoin-logo')
      expect(img.classes()).toContain('bitcoin-logo--md')
    })

    it('should apply base CSS class', () => {
      wrapper = mount(BitcoinLogo)
      const img = wrapper.find('img')
      expect(img.classes()).toContain('bitcoin-logo')
    })
  })

  describe('Size Prop Validation and logoSrc Computation', () => {
    it('should use SVG for small sizes (≤32px)', () => {
      const smallSizes = [
        { size: 'xs', expected: '/bitcoin-symbol.svg' },
        { size: 'sm', expected: '/bitcoin-symbol.svg' },
        { size: 'md', expected: '/bitcoin-symbol.svg' },
        { size: 16, expected: '/bitcoin-symbol.svg' },
        { size: 24, expected: '/bitcoin-symbol.svg' },
        { size: 32, expected: '/bitcoin-symbol.svg' }
      ]

      smallSizes.forEach(({ size, expected }) => {
        wrapper = mount(BitcoinLogo, {
          props: { size }
        })
        const img = wrapper.find('img')
        expect(img.attributes('src')).toBe(expected)
      })
    })

    it('should use PNG for large sizes (>32px)', () => {
      const largeSizes = [
        { size: 'lg', expected: '/bitcoin-symbol.png' },
        { size: 'xl', expected: '/bitcoin-symbol.png' },
        { size: 'hero', expected: '/bitcoin-symbol.png' },
        { size: 48, expected: '/bitcoin-symbol.png' },
        { size: 64, expected: '/bitcoin-symbol.png' },
        { size: 96, expected: '/bitcoin-symbol.png' }
      ]

      largeSizes.forEach(({ size, expected }) => {
        wrapper = mount(BitcoinLogo, {
          props: { size }
        })
        const img = wrapper.find('img')
        expect(img.attributes('src')).toBe(expected)
      })
    })

    it('should validate string size props correctly', () => {
      const validSizes = ['xs', 'sm', 'md', 'lg', 'xl', 'hero']
      
      validSizes.forEach(size => {
        expect(() => {
          wrapper = mount(BitcoinLogo, {
            props: { size }
          })
        }).not.toThrow()
      })
    })

    it('should validate numeric size props correctly', () => {
      const validNumericSizes = [1, 16, 32, 64, 128, 256]
      
      validNumericSizes.forEach(size => {
        expect(() => {
          wrapper = mount(BitcoinLogo, {
            props: { size }
          })
        }).not.toThrow()
      })
    })

    it('should apply correct size classes for string props', () => {
      const sizeClasses = [
        { size: 'xs', class: 'bitcoin-logo--xs' },
        { size: 'sm', class: 'bitcoin-logo--sm' },
        { size: 'md', class: 'bitcoin-logo--md' },
        { size: 'lg', class: 'bitcoin-logo--lg' },
        { size: 'xl', class: 'bitcoin-logo--xl' },
        { size: 'hero', class: 'bitcoin-logo--hero' }
      ]

      sizeClasses.forEach(({ size, class: expectedClass }) => {
        wrapper = mount(BitcoinLogo, {
          props: { size }
        })
        const img = wrapper.find('img')
        expect(img.classes()).toContain(expectedClass)
      })
    })

    it('should apply custom numeric sizes as inline styles', () => {
      const customSizes = [20, 40, 80, 120]
      
      customSizes.forEach(size => {
        wrapper = mount(BitcoinLogo, {
          props: { size }
        })
        const img = wrapper.find('img')
        expect(img.attributes('style')).toContain(`width: ${size}px`)
        expect(img.attributes('style')).toContain(`height: ${size}px`)
      })
    })
  })

  describe('Variant Prop Validation', () => {
    it('should validate variant prop correctly', () => {
      const validVariants = ['default', 'glow', 'subtle']
      
      validVariants.forEach(variant => {
        expect(() => {
          wrapper = mount(BitcoinLogo, {
            props: { variant }
          })
        }).not.toThrow()
      })
    })

    it('should apply variant CSS classes', () => {
      const variants = [
        { variant: 'glow', class: 'bitcoin-logo--glow' },
        { variant: 'subtle', class: 'bitcoin-logo--subtle' }
      ]

      variants.forEach(({ variant, class: expectedClass }) => {
        wrapper = mount(BitcoinLogo, {
          props: { variant }
        })
        const img = wrapper.find('img')
        expect(img.classes()).toContain(expectedClass)
      })
    })

    it('should not apply variant class for default variant', () => {
      wrapper = mount(BitcoinLogo, {
        props: { variant: 'default' }
      })
      const img = wrapper.find('img')
      expect(img.classes()).not.toContain('bitcoin-logo--default')
    })
  })

  describe('Animation Support', () => {
    it('should apply animation class when animated prop is true', () => {
      wrapper = mount(BitcoinLogo, {
        props: { animated: true }
      })
      const img = wrapper.find('img')
      expect(img.classes()).toContain('bitcoin-logo--animated')
    })

    it('should not apply animation class when animated prop is false', () => {
      wrapper = mount(BitcoinLogo, {
        props: { animated: false }
      })
      const img = wrapper.find('img')
      expect(img.classes()).not.toContain('bitcoin-logo--animated')
    })
  })

  describe('Accessibility Attributes', () => {
    it('should support custom aria-label', () => {
      const customAriaLabel = 'Custom Bitcoin Logo'
      wrapper = mount(BitcoinLogo, {
        props: { ariaLabel: customAriaLabel }
      })
      const img = wrapper.find('img')
      expect(img.attributes('aria-label')).toBe(customAriaLabel)
    })

    it('should support custom alt text', () => {
      const customAltText = 'Custom Alt Text'
      wrapper = mount(BitcoinLogo, {
        props: { altText: customAltText }
      })
      const img = wrapper.find('img')
      expect(img.attributes('alt')).toBe(customAltText)
    })

    it('should have default accessibility attributes', () => {
      wrapper = mount(BitcoinLogo)
      const img = wrapper.find('img')
      expect(img.attributes('aria-label')).toBe('Bitcoin Logo')
      expect(img.attributes('alt')).toBe('Bitcoin')
    })
  })

  describe('Error Handling', () => {
    it('should handle load events and emit logo-loaded', async () => {
      wrapper = mount(BitcoinLogo, {
        props: { size: 'md' }
      })
      
      const img = wrapper.find('img')
      await img.trigger('load')
      
      expect(wrapper.emitted('logo-loaded')).toBeTruthy()
      expect(wrapper.emitted('logo-loaded')[0][0]).toEqual({
        src: '/bitcoin-symbol.svg',
        size: 32
      })
    })

    it('should handle error events and emit logo-error', async () => {
      // Mock console.warn to avoid noise in test output
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      wrapper = mount(BitcoinLogo, {
        props: { size: 'lg' }
      })
      
      const img = wrapper.find('img')
      await img.trigger('error')
      
      expect(wrapper.emitted('logo-error')).toBeTruthy()
      expect(wrapper.emitted('logo-error')[0][0]).toEqual({
        src: '/bitcoin-symbol.png',
        size: 48
      })
      
      expect(consoleSpy).toHaveBeenCalledWith('Bitcoin logo failed to load:', '/bitcoin-symbol.png')
      consoleSpy.mockRestore()
    })

    it('should track loading state correctly', async () => {
      wrapper = mount(BitcoinLogo)
      
      // Initially not loaded, no error
      expect(wrapper.vm.logoLoaded).toBe(false)
      expect(wrapper.vm.logoError).toBe(false)
      
      // Trigger load event
      const img = wrapper.find('img')
      await img.trigger('load')
      
      expect(wrapper.vm.logoLoaded).toBe(true)
      expect(wrapper.vm.logoError).toBe(false)
    })

    it('should track error state correctly', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      wrapper = mount(BitcoinLogo)
      
      // Trigger error event
      const img = wrapper.find('img')
      await img.trigger('error')
      
      expect(wrapper.vm.logoLoaded).toBe(false)
      expect(wrapper.vm.logoError).toBe(true)
      
      consoleSpy.mockRestore()
    })
  })

  describe('Complex Prop Combinations', () => {
    it('should handle multiple props correctly', () => {
      wrapper = mount(BitcoinLogo, {
        props: {
          size: 'lg',
          variant: 'glow',
          animated: true,
          ariaLabel: 'Animated Glowing Bitcoin Logo',
          altText: 'Bitcoin Symbol'
        }
      })
      
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.png') // lg size uses PNG
      expect(img.attributes('aria-label')).toBe('Animated Glowing Bitcoin Logo')
      expect(img.attributes('alt')).toBe('Bitcoin Symbol')
      expect(img.classes()).toContain('bitcoin-logo')
      expect(img.classes()).toContain('bitcoin-logo--lg')
      expect(img.classes()).toContain('bitcoin-logo--glow')
      expect(img.classes()).toContain('bitcoin-logo--animated')
    })

    it('should handle numeric size with variant and animation', () => {
      wrapper = mount(BitcoinLogo, {
        props: {
          size: 50,
          variant: 'subtle',
          animated: true
        }
      })
      
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.png') // 50px > 32px uses PNG
      expect(img.attributes('style')).toContain('width: 50px')
      expect(img.attributes('style')).toContain('height: 50px')
      expect(img.classes()).toContain('bitcoin-logo--subtle')
      expect(img.classes()).toContain('bitcoin-logo--animated')
    })
  })

  describe('Edge Cases', () => {
    it('should handle boundary size of 32px correctly', () => {
      wrapper = mount(BitcoinLogo, {
        props: { size: 32 }
      })
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.svg') // 32px should use SVG
    })

    it('should handle boundary size of 33px correctly', () => {
      wrapper = mount(BitcoinLogo, {
        props: { size: 33 }
      })
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.png') // 33px should use PNG
    })

    it('should handle minimum size correctly', () => {
      wrapper = mount(BitcoinLogo, {
        props: { size: 1 }
      })
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.svg')
      expect(img.attributes('style')).toContain('width: 1px')
      expect(img.attributes('style')).toContain('height: 1px')
    })

    it('should handle maximum size correctly', () => {
      wrapper = mount(BitcoinLogo, {
        props: { size: 256 }
      })
      const img = wrapper.find('img')
      expect(img.attributes('src')).toBe('/bitcoin-symbol.png')
      expect(img.attributes('style')).toContain('width: 256px')
      expect(img.attributes('style')).toContain('height: 256px')
    })
  })
})