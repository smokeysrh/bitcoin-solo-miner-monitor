#!/bin/bash
# Test script for Linux package creation system
# This script validates the package creation process without requiring full builds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
TEST_DIR="/tmp/bitcoin-miner-package-test"
TEST_APP_DIR="$TEST_DIR/app"
TEST_DIST_DIR="$TEST_DIR/dist"
TEST_VERSION="1.0.0-test"

cleanup() {
    log_info "Cleaning up test environment..."
    rm -rf "$TEST_DIR"
}

trap cleanup EXIT

log_info "Starting Linux package creation system tests..."

# Create test environment
log_info "Setting up test environment..."
mkdir -p "$TEST_APP_DIR"
mkdir -p "$TEST_DIST_DIR"

# Create minimal test application structure
log_info "Creating test application structure..."
cat > "$TEST_APP_DIR/run.py" << 'EOF'
#!/usr/bin/env python3
"""Test Bitcoin Solo Miner Monitor application"""
import sys
print("Bitcoin Solo Miner Monitor Test Application")
print(f"Python version: {sys.version}")
print("Application started successfully!")
EOF

cat > "$TEST_APP_DIR/requirements.txt" << 'EOF'
# Test requirements
requests>=2.25.0
flask>=2.0.0
EOF

# Copy assets if they exist
if [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.png" ]; then
    mkdir -p "$TEST_APP_DIR/assets"
    cp "$PROJECT_ROOT/assets/bitcoin-symbol.png" "$TEST_APP_DIR/assets/"
fi

# Copy installer templates
if [ -d "$SCRIPT_DIR/templates" ]; then
    cp -r "$SCRIPT_DIR/templates" "$TEST_APP_DIR/installer/linux/"
fi

# Test 1: Validate build scripts exist and are executable
log_info "Test 1: Validating build scripts..."

REQUIRED_SCRIPTS=(
    "build_packages.sh"
    "build_deb.sh" 
    "build_rpm.sh"
    "build_appimage.sh"
    "create_all_packages.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    script_path="$SCRIPT_DIR/$script"
    if [ -f "$script_path" ]; then
        if [ -x "$script_path" ]; then
            log_success "Script exists and is executable: $script"
        else
            log_warning "Script exists but not executable: $script"
        fi
    else
        log_error "Required script missing: $script"
        exit 1
    fi
done

# Test 2: Validate template files
log_info "Test 2: Validating template files..."

REQUIRED_TEMPLATES=(
    "bitcoin-solo-miner-monitor.desktop"
    "bitcoin-solo-miner-monitor@.service"
    "config.ini"
)

for template in "${REQUIRED_TEMPLATES[@]}"; do
    template_path="$SCRIPT_DIR/templates/$template"
    if [ -f "$template_path" ]; then
        log_success "Template exists: $template"
    else
        log_warning "Template missing: $template"
    fi
done

# Test 3: Test build system help/usage
log_info "Test 3: Testing build system help output..."

if "$SCRIPT_DIR/create_all_packages.sh" --help >/dev/null 2>&1; then
    log_success "Main build script help works"
else
    log_warning "Main build script help may have issues"
fi

# Test 4: Test build system validation (dry run)
log_info "Test 4: Testing build system validation..."

# Test with invalid package type
if "$SCRIPT_DIR/create_all_packages.sh" --type invalid 2>/dev/null; then
    log_error "Build system should reject invalid package types"
else
    log_success "Build system properly validates package types"
fi

# Test 5: Check for required system tools
log_info "Test 5: Checking for required system tools..."

SYSTEM_TOOLS=(
    "python3:Python 3 interpreter"
    "git:Git version control"
    "tar:Archive creation"
    "gzip:Compression"
)

OPTIONAL_TOOLS=(
    "dpkg-deb:DEB package creation"
    "rpmbuild:RPM package creation"
    "wget:AppImage tool download"
)

for tool_info in "${SYSTEM_TOOLS[@]}"; do
    tool="${tool_info%%:*}"
    desc="${tool_info##*:}"
    if command -v "$tool" >/dev/null 2>&1; then
        log_success "Required tool available: $tool ($desc)"
    else
        log_error "Required tool missing: $tool ($desc)"
    fi
done

for tool_info in "${OPTIONAL_TOOLS[@]}"; do
    tool="${tool_info%%:*}"
    desc="${tool_info##*:}"
    if command -v "$tool" >/dev/null 2>&1; then
        log_success "Optional tool available: $tool ($desc)"
    else
        log_warning "Optional tool missing: $tool ($desc)"
    fi
done

# Test 6: Validate desktop entry template
log_info "Test 6: Validating desktop entry template..."

DESKTOP_TEMPLATE="$SCRIPT_DIR/templates/bitcoin-solo-miner-monitor.desktop"
if [ -f "$DESKTOP_TEMPLATE" ]; then
    # Check for required desktop entry fields
    REQUIRED_FIELDS=("Name=" "Exec=" "Icon=" "Type=Application")
    
    for field in "${REQUIRED_FIELDS[@]}"; do
        if grep -q "^$field" "$DESKTOP_TEMPLATE"; then
            log_success "Desktop entry has required field: $field"
        else
            log_error "Desktop entry missing required field: $field"
        fi
    done
    
    # Check for multi-language support
    if grep -q "Name\[" "$DESKTOP_TEMPLATE"; then
        log_success "Desktop entry has multi-language support"
    else
        log_warning "Desktop entry lacks multi-language support"
    fi
else
    log_warning "Desktop entry template not found"
fi

# Test 7: Validate systemd service template
log_info "Test 7: Validating systemd service template..."

SERVICE_TEMPLATE="$SCRIPT_DIR/templates/bitcoin-solo-miner-monitor@.service"
if [ -f "$SERVICE_TEMPLATE" ]; then
    # Check for required systemd service sections
    REQUIRED_SECTIONS=("[Unit]" "[Service]" "[Install]")
    
    for section in "${REQUIRED_SECTIONS[@]}"; do
        if grep -q "^$section" "$SERVICE_TEMPLATE"; then
            log_success "Service template has required section: $section"
        else
            log_error "Service template missing required section: $section"
        fi
    done
    
    # Check for security settings
    if grep -q "NoNewPrivileges=true" "$SERVICE_TEMPLATE"; then
        log_success "Service template has security hardening"
    else
        log_warning "Service template lacks security hardening"
    fi
else
    log_warning "Systemd service template not found"
fi

# Test 8: Test minimal package creation (if tools available)
log_info "Test 8: Testing minimal package creation..."

if command -v dpkg-deb >/dev/null 2>&1; then
    log_info "Attempting minimal DEB package creation test..."
    
    # Create minimal DEB structure
    MINIMAL_DEB_DIR="$TEST_DIR/minimal_deb"
    mkdir -p "$MINIMAL_DEB_DIR/DEBIAN"
    mkdir -p "$MINIMAL_DEB_DIR/opt/test-app"
    
    # Create minimal control file
    cat > "$MINIMAL_DEB_DIR/DEBIAN/control" << EOF
Package: bitcoin-solo-miner-monitor-test
Version: $TEST_VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: test@example.com
Description: Test package for Bitcoin Solo Miner Monitor
EOF
    
    # Create test file
    echo "Test application" > "$MINIMAL_DEB_DIR/opt/test-app/test.txt"
    
    # Try to build minimal DEB
    if dpkg-deb --build "$MINIMAL_DEB_DIR" "$TEST_DIST_DIR/test.deb" >/dev/null 2>&1; then
        log_success "Minimal DEB package creation works"
        rm -f "$TEST_DIST_DIR/test.deb"
    else
        log_warning "Minimal DEB package creation failed"
    fi
else
    log_info "Skipping DEB test (dpkg-deb not available)"
fi

# Summary
log_info "Test Summary:"
log_info "============="

TOTAL_TESTS=8
PASSED_TESTS=0

# Count successful tests (this is a simplified count)
if [ -f "$SCRIPT_DIR/build_packages.sh" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi

if [ -f "$SCRIPT_DIR/templates/bitcoin-solo-miner-monitor.desktop" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi

if command -v python3 >/dev/null 2>&1; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi

log_info "Tests completed: $PASSED_TESTS/$TOTAL_TESTS core components validated"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    log_success "All core tests passed! Package creation system is ready."
    exit 0
elif [ $PASSED_TESTS -gt $((TOTAL_TESTS / 2)) ]; then
    log_warning "Most tests passed. System should work with minor issues."
    exit 0
else
    log_error "Multiple test failures. Please review the system setup."
    exit 1
fi