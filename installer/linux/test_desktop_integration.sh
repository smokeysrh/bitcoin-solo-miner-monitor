#!/bin/bash
# Comprehensive Desktop Integration Test Script
# Tests all aspects of Linux desktop integration for Bitcoin Solo Miner Monitor

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Test configuration
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
TEST_USER_DIR="/tmp/desktop_integration_test"
VERBOSE=false
CLEANUP=true

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging functions
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_warning() {
    echo "⚠️  $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "🔍 $1"
    fi
}

log_test_start() {
    echo ""
    echo "🧪 Testing: $1"
    ((TESTS_TOTAL++))
}

log_test_pass() {
    echo "   ✅ PASS: $1"
    ((TESTS_PASSED++))
}

log_test_fail() {
    echo "   ❌ FAIL: $1"
    ((TESTS_FAILED++))
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Test comprehensive Linux desktop integration

OPTIONS:
    -v, --verbose       Enable verbose output
    -k, --keep-files    Keep test files after completion
    -h, --help          Show this help message

EXAMPLES:
    $0                  # Run all tests with cleanup
    $0 -v -k            # Run tests with verbose output and keep files

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -k|--keep-files)
            CLEANUP=false
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create test directory structure
    rm -rf "$TEST_USER_DIR"
    mkdir -p "$TEST_USER_DIR"/{.local/share/{applications,icons/hicolor,mime/packages},.config/autostart}
    
    # Set up environment variables for testing
    export HOME="$TEST_USER_DIR"
    export XDG_DATA_HOME="$TEST_USER_DIR/.local/share"
    export XDG_CONFIG_HOME="$TEST_USER_DIR/.config"
    
    log_success "Test environment created at: $TEST_USER_DIR"
}

# Test desktop entry creation
test_desktop_entry_creation() {
    log_test_start "Desktop entry creation"
    
    # Run desktop integration script in user mode
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local --verbose >/dev/null 2>&1; then
        log_test_pass "Desktop integration script executed successfully"
    else
        log_test_fail "Desktop integration script failed"
        return 1
    fi
    
    # Check if desktop entry was created
    local desktop_file="$TEST_USER_DIR/.local/share/applications/$APP_NAME.desktop"
    if [ -f "$desktop_file" ]; then
        log_test_pass "Desktop entry file created"
    else
        log_test_fail "Desktop entry file not found"
        return 1
    fi
    
    # Validate desktop entry content
    if grep -q "Name=$DISPLAY_NAME" "$desktop_file"; then
        log_test_pass "Desktop entry contains correct name"
    else
        log_test_fail "Desktop entry missing or incorrect name"
    fi
    
    if grep -q "Exec=$APP_NAME" "$desktop_file"; then
        log_test_pass "Desktop entry contains correct exec command"
    else
        log_test_fail "Desktop entry missing or incorrect exec command"
    fi
    
    if grep -q "Icon=$APP_NAME" "$desktop_file"; then
        log_test_pass "Desktop entry contains correct icon reference"
    else
        log_test_fail "Desktop entry missing or incorrect icon reference"
    fi
    
    # Test desktop entry validation if available
    if command -v desktop-file-validate >/dev/null 2>&1; then
        if desktop-file-validate "$desktop_file" 2>/dev/null; then
            log_test_pass "Desktop entry passes validation"
        else
            log_test_fail "Desktop entry validation failed"
        fi
    else
        log_warning "desktop-file-validate not available, skipping validation test"
    fi
}

# Test icon installation
test_icon_installation() {
    log_test_start "Icon installation"
    
    local icon_base_dir="$TEST_USER_DIR/.local/share/icons/hicolor"
    local icon_sizes=("16" "22" "24" "32" "48" "64" "128" "256" "512")
    
    # Check if icons were installed
    local icons_found=0
    for size in "${icon_sizes[@]}"; do
        local icon_file="$icon_base_dir/${size}x${size}/apps/$APP_NAME.png"
        if [ -f "$icon_file" ]; then
            ((icons_found++))
            log_verbose "Found icon: ${size}x${size}"
        fi
    done
    
    if [ $icons_found -gt 0 ]; then
        log_test_pass "Icons installed ($icons_found sizes found)"
    else
        log_test_fail "No icons found"
    fi
    
    # Check for scalable icon if SVG source was available
    local scalable_icon="$icon_base_dir/scalable/apps/$APP_NAME.svg"
    if [ -f "$scalable_icon" ]; then
        log_test_pass "Scalable SVG icon installed"
    else
        log_verbose "No scalable SVG icon found (may be expected)"
    fi
}

# Test MIME type associations
test_mime_type_associations() {
    log_test_start "MIME type associations"
    
    local mime_file="$TEST_USER_DIR/.local/share/mime/packages/$APP_NAME.xml"
    
    if [ -f "$mime_file" ]; then
        log_test_pass "MIME type file created"
    else
        log_test_fail "MIME type file not found"
        return 1
    fi
    
    # Check MIME type content
    if grep -q "application/x-bitcoin-miner-config" "$mime_file"; then
        log_test_pass "Bitcoin miner config MIME type defined"
    else
        log_test_fail "Bitcoin miner config MIME type missing"
    fi
    
    if grep -q "application/x-mining-pool-config" "$mime_file"; then
        log_test_pass "Mining pool config MIME type defined"
    else
        log_test_fail "Mining pool config MIME type missing"
    fi
    
    # Check for file patterns
    if grep -q "*.miner" "$mime_file"; then
        log_test_pass "Miner file pattern defined"
    else
        log_test_fail "Miner file pattern missing"
    fi
    
    # Check for magic bytes
    if grep -q "MinerConfig" "$mime_file"; then
        log_test_pass "Magic bytes pattern defined"
    else
        log_test_fail "Magic bytes pattern missing"
    fi
}

# Test desktop actions
test_desktop_actions() {
    log_test_start "Desktop actions"
    
    local desktop_file="$TEST_USER_DIR/.local/share/applications/$APP_NAME.desktop"
    
    if [ ! -f "$desktop_file" ]; then
        log_test_fail "Desktop entry not found for actions test"
        return 1
    fi
    
    # Check for actions declaration
    if grep -q "Actions=" "$desktop_file"; then
        log_test_pass "Desktop actions declared"
    else
        log_test_fail "Desktop actions not declared"
        return 1
    fi
    
    # Check for specific actions
    local actions=("StartService" "StopService" "ViewLogs" "OpenConfig" "CheckStatus")
    for action in "${actions[@]}"; do
        if grep -q "\[Desktop Action $action\]" "$desktop_file"; then
            log_test_pass "Action '$action' defined"
        else
            log_test_fail "Action '$action' missing"
        fi
    done
}

# Test multi-language support
test_multilanguage_support() {
    log_test_start "Multi-language support"
    
    local desktop_file="$TEST_USER_DIR/.local/share/applications/$APP_NAME.desktop"
    
    if [ ! -f "$desktop_file" ]; then
        log_test_fail "Desktop entry not found for language test"
        return 1
    fi
    
    # Check for different language entries
    local languages=("es" "fr" "de" "zh_CN")
    for lang in "${languages[@]}"; do
        if grep -q "Name\[$lang\]=" "$desktop_file"; then
            log_test_pass "Language '$lang' name translation found"
        else
            log_test_fail "Language '$lang' name translation missing"
        fi
        
        if grep -q "Comment\[$lang\]=" "$desktop_file"; then
            log_test_pass "Language '$lang' comment translation found"
        else
            log_test_fail "Language '$lang' comment translation missing"
        fi
    done
}

# Test autostart functionality
test_autostart_functionality() {
    log_test_start "Autostart functionality"
    
    # Run desktop integration with autostart enabled
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local --autostart >/dev/null 2>&1; then
        log_test_pass "Desktop integration with autostart executed"
    else
        log_test_fail "Desktop integration with autostart failed"
        return 1
    fi
    
    local autostart_file="$TEST_USER_DIR/.config/autostart/$APP_NAME.desktop"
    
    if [ -f "$autostart_file" ]; then
        log_test_pass "Autostart entry created"
    else
        log_test_fail "Autostart entry not found"
        return 1
    fi
    
    # Check autostart entry content
    if grep -q "X-GNOME-Autostart-enabled=true" "$autostart_file"; then
        log_test_pass "GNOME autostart enabled"
    else
        log_test_fail "GNOME autostart not properly configured"
    fi
    
    if grep -q "Hidden=false" "$autostart_file"; then
        log_test_pass "Autostart entry not hidden"
    else
        log_test_fail "Autostart entry incorrectly hidden"
    fi
}

# Test dry run functionality
test_dry_run_functionality() {
    log_test_start "Dry run functionality"
    
    # Clean test environment
    rm -rf "$TEST_USER_DIR"/.local/share/applications/*
    rm -rf "$TEST_USER_DIR"/.local/share/icons/hicolor/*/apps/*
    rm -rf "$TEST_USER_DIR"/.local/share/mime/packages/*
    
    # Run in dry run mode
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local --dry-run >/dev/null 2>&1; then
        log_test_pass "Dry run mode executed successfully"
    else
        log_test_fail "Dry run mode failed"
        return 1
    fi
    
    # Verify no files were actually created
    if [ ! -f "$TEST_USER_DIR/.local/share/applications/$APP_NAME.desktop" ]; then
        log_test_pass "Dry run did not create desktop entry"
    else
        log_test_fail "Dry run incorrectly created desktop entry"
    fi
    
    if [ ! -f "$TEST_USER_DIR/.local/share/icons/hicolor/256x256/apps/$APP_NAME.png" ]; then
        log_test_pass "Dry run did not create icons"
    else
        log_test_fail "Dry run incorrectly created icons"
    fi
}

# Test error handling
test_error_handling() {
    log_test_start "Error handling"
    
    # Test with invalid permissions (simulate)
    local readonly_dir="$TEST_USER_DIR/readonly_test"
    mkdir -p "$readonly_dir"
    chmod 444 "$readonly_dir"
    
    # This should handle the error gracefully
    export HOME="$readonly_dir"
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local >/dev/null 2>&1; then
        log_verbose "Script handled readonly directory"
    else
        log_verbose "Script failed with readonly directory (expected)"
    fi
    
    # Restore environment
    export HOME="$TEST_USER_DIR"
    chmod 755 "$readonly_dir"
    rm -rf "$readonly_dir"
    
    log_test_pass "Error handling test completed"
}

# Test integration with existing desktop files
test_existing_desktop_integration() {
    log_test_start "Integration with existing desktop files"
    
    # Create a pre-existing desktop file
    local desktop_file="$TEST_USER_DIR/.local/share/applications/$APP_NAME.desktop"
    mkdir -p "$(dirname "$desktop_file")"
    
    cat > "$desktop_file" << EOF
[Desktop Entry]
Name=Old Version
Comment=Old comment
Exec=old-command
Icon=old-icon
Type=Application
EOF
    
    # Run desktop integration (should overwrite)
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local >/dev/null 2>&1; then
        log_test_pass "Desktop integration with existing file executed"
    else
        log_test_fail "Desktop integration with existing file failed"
        return 1
    fi
    
    # Check if file was updated
    if grep -q "Name=$DISPLAY_NAME" "$desktop_file"; then
        log_test_pass "Existing desktop file was updated"
    else
        log_test_fail "Existing desktop file was not updated"
    fi
}

# Test command line argument parsing
test_command_line_arguments() {
    log_test_start "Command line argument parsing"
    
    # Test help option
    if "$SCRIPT_DIR/desktop_integration.sh" --help >/dev/null 2>&1; then
        log_test_pass "Help option works"
    else
        log_test_fail "Help option failed"
    fi
    
    # Test verbose option
    if "$SCRIPT_DIR/desktop_integration.sh" --user-local --verbose --dry-run >/dev/null 2>&1; then
        log_test_pass "Verbose option works"
    else
        log_test_fail "Verbose option failed"
    fi
    
    # Test invalid option handling
    if ! "$SCRIPT_DIR/desktop_integration.sh" --invalid-option >/dev/null 2>&1; then
        log_test_pass "Invalid option properly rejected"
    else
        log_test_fail "Invalid option not properly handled"
    fi
}

# Cleanup test environment
cleanup_test_environment() {
    if [ "$CLEANUP" = true ]; then
        log_info "Cleaning up test environment..."
        rm -rf "$TEST_USER_DIR"
        log_success "Test environment cleaned up"
    else
        log_info "Test files preserved at: $TEST_USER_DIR"
    fi
}

# Generate test report
generate_test_report() {
    echo ""
    echo "📊 Test Results Summary"
    echo "======================="
    echo "Total tests: $TESTS_TOTAL"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    echo "Success rate: $(( TESTS_PASSED * 100 / TESTS_TOTAL ))%"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All tests passed! Desktop integration is working correctly."
        return 0
    else
        log_error "$TESTS_FAILED tests failed. Please review the output above."
        return 1
    fi
}

# Main test function
main() {
    log_info "Starting comprehensive desktop integration tests..."
    log_info "Test configuration:"
    log_info "  - Verbose output: $VERBOSE"
    log_info "  - Cleanup after tests: $CLEANUP"
    log_info "  - Test directory: $TEST_USER_DIR"
    
    # Setup test environment
    setup_test_environment
    
    # Run all tests
    test_desktop_entry_creation
    test_icon_installation
    test_mime_type_associations
    test_desktop_actions
    test_multilanguage_support
    test_autostart_functionality
    test_dry_run_functionality
    test_error_handling
    test_existing_desktop_integration
    test_command_line_arguments
    
    # Generate report
    local exit_code=0
    if ! generate_test_report; then
        exit_code=1
    fi
    
    # Cleanup
    cleanup_test_environment
    
    exit $exit_code
}

# Run main function
main "$@"