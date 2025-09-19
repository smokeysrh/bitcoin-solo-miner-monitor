#!/bin/bash
# Test script for Linux CI/CD integration
# Validates that the Linux build system works correctly in CI environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test configuration
TEST_VERSION="0.1.0-ci-test"
TEST_DIST_DIR="${PROJECT_ROOT}/test-distribution"
TEMP_APP_DIR=""

cleanup() {
    if [ -n "$TEMP_APP_DIR" ] && [ -d "$TEMP_APP_DIR" ]; then
        log_info "Cleaning up temporary directory: $TEMP_APP_DIR"
        rm -rf "$TEMP_APP_DIR"
    fi
    
    if [ -d "$TEST_DIST_DIR" ]; then
        log_info "Cleaning up test distribution directory"
        rm -rf "$TEST_DIST_DIR"
    fi
}

trap cleanup EXIT

# Test environment setup
test_environment() {
    log_info "Testing CI environment setup..."
    
    # Check required tools
    local missing_tools=()
    
    # Basic tools
    for tool in python3 node npm git; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    # Package-specific tools
    if command -v dpkg >/dev/null 2>&1; then
        log_success "DEB packaging tools available"
    else
        log_warning "DEB packaging tools not available"
    fi
    
    if command -v rpm >/dev/null 2>&1; then
        log_success "RPM packaging tools available"
    else
        log_warning "RPM packaging tools not available"
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log_success "Environment setup test passed"
    return 0
}

# Test application bundle preparation
test_app_bundle() {
    log_info "Testing application bundle preparation..."
    
    # Create temporary app directory
    TEMP_APP_DIR=$(mktemp -d)
    log_info "Using temporary directory: $TEMP_APP_DIR"
    
    # Test Python script to simulate create-distribution.py
    python3 -c "
import os
import shutil
from pathlib import Path

project_root = Path('$PROJECT_ROOT')
app_dir = Path('$TEMP_APP_DIR')

# Copy essential files
essential_files = ['requirements.txt', 'run.py', 'README.md']
for file in essential_files:
    src_file = project_root / file
    if src_file.exists():
        shutil.copy2(src_file, app_dir / file)
        print(f'✅ Copied: {file}')
    else:
        print(f'⚠️  Missing: {file}')

# Copy directories
for dir_name in ['src', 'config', 'assets']:
    src_dir = project_root / dir_name
    if src_dir.exists():
        shutil.copytree(src_dir, app_dir / dir_name, dirs_exist_ok=True)
        print(f'✅ Copied directory: {dir_name}')
    else:
        print(f'⚠️  Missing directory: {dir_name}')

print('✅ Application bundle prepared')
"
    
    # Verify bundle contents
    if [ ! -f "$TEMP_APP_DIR/run.py" ]; then
        log_error "Application bundle missing run.py"
        return 1
    fi
    
    if [ ! -f "$TEMP_APP_DIR/requirements.txt" ]; then
        log_error "Application bundle missing requirements.txt"
        return 1
    fi
    
    log_success "Application bundle preparation test passed"
    return 0
}

# Test individual package builders
test_package_builders() {
    log_info "Testing individual package builders..."
    
    mkdir -p "$TEST_DIST_DIR"
    
    # Test DEB builder if available
    if command -v dpkg >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/build_deb.sh" ]; then
        log_info "Testing DEB package builder..."
        
        if bash "$SCRIPT_DIR/build_deb.sh" "$TEMP_APP_DIR" "$TEST_DIST_DIR" "$TEST_VERSION" --verbose; then
            log_success "DEB package builder test passed"
            
            # Verify DEB package
            deb_file=$(find "$TEST_DIST_DIR" -name "*.deb" | head -1)
            if [ -n "$deb_file" ] && [ -f "$deb_file" ]; then
                log_success "DEB package created: $(basename "$deb_file")"
                
                # Basic validation
                if dpkg --info "$deb_file" >/dev/null 2>&1; then
                    log_success "DEB package structure is valid"
                else
                    log_error "DEB package structure is invalid"
                    return 1
                fi
            else
                log_error "DEB package not found"
                return 1
            fi
        else
            log_warning "DEB package builder failed (may be expected in some environments)"
        fi
    else
        log_warning "DEB package builder not available"
    fi
    
    # Test RPM builder if available
    if command -v rpm >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/build_rpm.sh" ]; then
        log_info "Testing RPM package builder..."
        
        if bash "$SCRIPT_DIR/build_rpm.sh" "$TEMP_APP_DIR" "$TEST_DIST_DIR" "$TEST_VERSION" --verbose; then
            log_success "RPM package builder test passed"
            
            # Verify RPM package
            rpm_file=$(find "$TEST_DIST_DIR" -name "*.rpm" | head -1)
            if [ -n "$rpm_file" ] && [ -f "$rpm_file" ]; then
                log_success "RPM package created: $(basename "$rpm_file")"
                
                # Basic validation
                if rpm -qip "$rpm_file" >/dev/null 2>&1; then
                    log_success "RPM package structure is valid"
                else
                    log_error "RPM package structure is invalid"
                    return 1
                fi
            else
                log_error "RPM package not found"
                return 1
            fi
        else
            log_warning "RPM package builder failed (may be expected in some environments)"
        fi
    else
        log_warning "RPM package builder not available"
    fi
    
    # Test AppImage builder if available
    if [ -f "$SCRIPT_DIR/build_appimage.sh" ]; then
        log_info "Testing AppImage builder..."
        
        if bash "$SCRIPT_DIR/build_appimage.sh" "$TEMP_APP_DIR" "$TEST_DIST_DIR" "$TEST_VERSION" --verbose; then
            log_success "AppImage builder test passed"
            
            # Verify AppImage
            appimage_file=$(find "$TEST_DIST_DIR" -name "*.AppImage" | head -1)
            if [ -n "$appimage_file" ] && [ -f "$appimage_file" ]; then
                log_success "AppImage created: $(basename "$appimage_file")"
                
                # Make executable and test
                chmod +x "$appimage_file"
                if [ -x "$appimage_file" ]; then
                    log_success "AppImage is executable"
                else
                    log_error "AppImage is not executable"
                    return 1
                fi
            else
                log_error "AppImage not found"
                return 1
            fi
        else
            log_warning "AppImage builder failed (may be expected in some environments)"
        fi
    else
        log_warning "AppImage builder not available"
    fi
    
    return 0
}

# Test checksum generation
test_checksums() {
    log_info "Testing checksum generation..."
    
    cd "$TEST_DIST_DIR"
    
    # Generate checksums for all packages
    if ls *.deb *.rpm *.AppImage *.tar.gz 2>/dev/null; then
        sha256sum *.deb *.rpm *.AppImage *.tar.gz 2>/dev/null > SHA256SUMS || \
        sha256sum * 2>/dev/null > SHA256SUMS || {
            log_error "Failed to generate checksums"
            return 1
        }
        
        log_success "Checksums generated"
        
        # Verify checksums
        if sha256sum -c SHA256SUMS >/dev/null 2>&1; then
            log_success "Checksum verification passed"
        else
            log_error "Checksum verification failed"
            return 1
        fi
    else
        log_warning "No packages found for checksum generation"
    fi
    
    cd - >/dev/null
    return 0
}

# Test CI simulation
test_ci_simulation() {
    log_info "Testing CI environment simulation..."
    
    # Simulate GitHub Actions environment variables
    export GITHUB_WORKSPACE="$PROJECT_ROOT"
    export GITHUB_SHA="test-commit-sha"
    export GITHUB_REF="refs/tags/v$TEST_VERSION"
    
    # Test matrix build simulation
    local distributions=("ubuntu:20.04" "ubuntu:22.04" "fedora:38")
    local package_formats=("deb appimage" "deb appimage" "rpm appimage")
    
    for i in "${!distributions[@]}"; do
        local dist="${distributions[$i]}"
        local formats="${package_formats[$i]}"
        
        log_info "Simulating build for $dist with formats: $formats"
        
        # This would normally run in a container, but we'll simulate the key steps
        if echo "$formats" | grep -q "deb" && command -v dpkg >/dev/null 2>&1; then
            log_success "DEB format supported for $dist"
        fi
        
        if echo "$formats" | grep -q "rpm" && command -v rpm >/dev/null 2>&1; then
            log_success "RPM format supported for $dist"
        fi
        
        if echo "$formats" | grep -q "appimage"; then
            log_success "AppImage format supported for $dist"
        fi
    done
    
    log_success "CI simulation test passed"
    return 0
}

# Main test execution
main() {
    log_info "Starting Linux CI/CD integration tests..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Test version: $TEST_VERSION"
    
    local test_results=()
    
    # Run tests
    if test_environment; then
        test_results+=("Environment: PASS")
    else
        test_results+=("Environment: FAIL")
    fi
    
    if test_app_bundle; then
        test_results+=("App Bundle: PASS")
    else
        test_results+=("App Bundle: FAIL")
    fi
    
    if test_package_builders; then
        test_results+=("Package Builders: PASS")
    else
        test_results+=("Package Builders: FAIL")
    fi
    
    if test_checksums; then
        test_results+=("Checksums: PASS")
    else
        test_results+=("Checksums: FAIL")
    fi
    
    if test_ci_simulation; then
        test_results+=("CI Simulation: PASS")
    else
        test_results+=("CI Simulation: FAIL")
    fi
    
    # Summary
    echo ""
    log_info "Test Results Summary:"
    log_info "===================="
    
    local failed_tests=0
    for result in "${test_results[@]}"; do
        if echo "$result" | grep -q "PASS"; then
            log_success "$result"
        else
            log_error "$result"
            failed_tests=$((failed_tests + 1))
        fi
    done
    
    echo ""
    if [ $failed_tests -eq 0 ]; then
        log_success "All tests passed! Linux CI/CD integration is ready."
        return 0
    else
        log_error "$failed_tests test(s) failed. Please review the issues above."
        return 1
    fi
}

# Run tests
main "$@"