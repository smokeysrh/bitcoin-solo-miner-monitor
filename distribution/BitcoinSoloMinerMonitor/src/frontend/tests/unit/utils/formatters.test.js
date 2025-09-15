import { describe, it, expect } from 'vitest';
import { formatTemperature } from '../../../src/utils/formatters';

describe('formatTemperature', () => {
  it('should format decimal temperatures to whole numbers', () => {
    expect(formatTemperature(65.7)).toBe('66°C');
    expect(formatTemperature(72.3)).toBe('72°C');
    expect(formatTemperature(80.9)).toBe('81°C');
  });

  it('should handle whole number temperatures', () => {
    expect(formatTemperature(65)).toBe('65°C');
    expect(formatTemperature(72)).toBe('72°C');
    expect(formatTemperature(80)).toBe('80°C');
  });

  it('should handle string inputs', () => {
    expect(formatTemperature('65.7')).toBe('66°C');
    expect(formatTemperature('72.3')).toBe('72°C');
    expect(formatTemperature('80')).toBe('80°C');
  });

  it('should handle edge cases', () => {
    expect(formatTemperature(null)).toBe('N/A');
    expect(formatTemperature(undefined)).toBe('N/A');
    expect(formatTemperature('')).toBe('N/A');
    expect(formatTemperature('invalid')).toBe('N/A');
    expect(formatTemperature(NaN)).toBe('N/A');
  });

  it('should handle zero and negative temperatures', () => {
    expect(formatTemperature(0)).toBe('0°C');
    expect(formatTemperature(-5.7)).toBe('-6°C');
    expect(formatTemperature(-10)).toBe('-10°C');
  });

  it('should round correctly using Math.round', () => {
    expect(formatTemperature(65.4)).toBe('65°C'); // rounds down
    expect(formatTemperature(65.5)).toBe('66°C'); // rounds up
    expect(formatTemperature(65.6)).toBe('66°C'); // rounds up
  });
});