# Bitaxe Models Research and Specifications

## Overview
Based on available information and community knowledge, here are the main Bitaxe models and their characteristics:

## Bitaxe Model Lineup

### 1. Bitaxe Ultra
- **ASIC Chip**: BM1366
- **Hashrate**: ~0.5 TH/s (500 GH/s)
- **Power Consumption**: ~15W
- **Efficiency**: ~30 W/TH
- **Board Versions**: 100-200 series
- **Status**: Older model

### 2. Bitaxe Supra
- **ASIC Chip**: BM1368 
- **Hashrate**: ~15-20 TH/s
- **Power Consumption**: ~15-20W
- **Efficiency**: ~1 W/TH (very efficient)
- **Board Versions**: 300-400 series
- **Status**: High-performance single ASIC

### 3. Bitaxe Gamma
- **ASIC Chip**: BM1397 OR BM1370
- **Hashrate**: 
  - BM1397 variant: ~0.4-0.6 TH/s (400-600 GH/s)
  - BM1370 variant: ~0.6-1.2 TH/s (600-1200 GH/s)
- **Power Consumption**: ~15-25W
- **Efficiency**: ~20-40 W/TH
- **Board Versions**: 200-500 series
- **Status**: Popular mid-range model with multiple ASIC variants

### 4. Bitaxe Hex
- **ASIC Chip**: BM1370
- **Hashrate**: ~1.0-1.4 TH/s (1000-1400 GH/s)
- **Power Consumption**: ~15-25W
- **Efficiency**: ~15-25 W/TH
- **Board Versions**: 600+ series
- **Status**: Newer high-performance model

## Key Detection Challenges

### BM1370 Confusion
The main issue is that **both Bitaxe Gamma and Bitaxe Hex can use BM1370 chips**, making ASIC-based detection insufficient.

### Overlapping Specifications
- **Hashrate Overlap**: Gamma (BM1370) and Hex can both achieve 1+ TH/s
- **Power Overlap**: Both models have similar power consumption ranges
- **Efficiency Overlap**: Performance characteristics can overlap

## Reliable Differentiation Methods

### 1. Board Version (Most Reliable)
- **Gamma**: Typically 200-500 series board versions
- **Hex**: Typically 600+ series board versions
- **Confidence**: High (90%+)

### 2. Firmware Version Patterns
- Different models may have different firmware version patterns
- Need to analyze version strings for model-specific indicators

### 3. Hardware Characteristics
- **Core Count**: Different models may have different core counts
- **Frequency Ranges**: Operating frequency ranges may differ
- **Voltage Patterns**: Core voltage settings may be model-specific

### 4. Performance Characteristics
- **Efficiency Curves**: Each model has characteristic efficiency patterns
- **Temperature Behavior**: Thermal characteristics may differ
- **Power Draw Patterns**: Power consumption curves may be distinctive

## Proposed Detection Logic Priority

1. **Primary**: Board version analysis
2. **Secondary**: Firmware version patterns  
3. **Tertiary**: Hardware characteristics (core count, frequency)
4. **Quaternary**: Performance characteristics (efficiency, hashrate)
5. **Fallback**: Hostname hints or conservative default

## Research Gaps

Need to gather more data on:
- Exact board version ranges for each model
- Firmware version patterns by model
- Core count specifications by model
- Frequency range specifications by model
- Real-world performance data from multiple devices

## Recommendations

1. **Collect More Device Data**: Test multiple known devices of each model
2. **Community Input**: Consult Bitaxe community for model identification
3. **Conservative Approach**: When uncertain, use generic "Bitaxe (BM1370)" label
4. **User Override**: Allow manual model specification in UI
5. **Continuous Learning**: Update detection logic as more data becomes available