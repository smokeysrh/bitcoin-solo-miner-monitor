#!/bin/bash
# Comprehensive Linux Package Creator for Bitcoin Solo Miner Monitor
# Creates DEB, RPM, and AppImage packages using the enhanced build system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
APP_DIR="${PROJECT_ROOT}/build/linux"
DIST_DIR="${PROJECT_ROOT}/distribution"
VERSION="1.0.0"
PACKAGE_TYPES="all"
VERBOSE=false
CLEAN_BUILD=false
PARALLEL_BUILD=false

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

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --app-dir DIR       Application directory (default: $APP_DIR)"
    echo "  -d, --dist-dir DIR      Distribution directory (default: $DIST_DIR)"
    echo "  -v, --version VERSION   Package version (default: $VERSION)"
    echo "  -t, --type TYPE         Package type: deb, rpm, appimage, all (default: all)"
    echo "  --verbose               Enable verbose output"
    echo "  -c, --clean             Clean build directory before building"
    echo "  -p, --parallel          Build packages in parallel (experimental)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Build all package types"
    echo "  $0 -t deb                            # Build only DEB package"
    echo "  $0 -t rpm --verbose                  # Build RPM with verbose output"
    echo "  $0 -v 2.0.0 --clean                 # Build all with version 2.0.0, clean first"
    echo "  $0 -t appimage -d /tmp/dist          # Build AppImage to custom directory"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--app-dir)
            APP_DIR="$2"
            shift 2
            ;;
        -d|--dist-dir)
            DIST_DIR="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -t|--type)
            PACKAGE_TYPES="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -p|--parallel)
            PARALLEL_BUILD=true
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

# Validate package type
case "$PACKAGE_TYPES" in
    "deb"|"rpm"|"appimage"|"all")
        ;;
    *)
        log_error "Invalid package type: $PACKAGE_TYPES"
        log_error "Valid types: deb, rpm, appimage, all"
        exit 1
        ;;
esac

# Prepare build options
BUILD_OPTIONS=()
if [ "$VERBOSE" = true ]; then
    BUILD_OPTIONS+=("--verbose")
fi
if [ "$CLEAN_BUILD" = true ]; then
    BUILD_OPTIONS+=("--clean")
fi

# Validate directories
if [ ! -d "$APP_DIR" ]; then
    log_error "Application directory not found: $APP_DIR"
    log_info "Please build the application first or specify correct path with --app-dir"
    exit 1
fi

# Create distribution directory
mkdir -p "$DIST_DIR"

log_info "Starting Linux package creation..."
log_info "Application directory: $APP_DIR"
log_info "Distribution directory: $DIST_DIR"
log_info "Version: $VERSION"
log_info "Package types: $PACKAGE_TYPES"

# Build function for individual package types
build_package() {
    local package_type="$1"
    local build_script="$SCRIPT_DIR/build_${package_type}.sh"
    
    if [ ! -f "$build_script" ]; then
        log_error "Build script not found: $build_script"
        return 1
    fi
    
    log_info "Building $package_type package..."
    
    if "$build_script" "$APP_DIR" "$DIST_DIR" "$VERSION" "${BUILD_OPTIONS[@]}"; then
        log_success "$package_type package built successfully"
        return 0
    else
        log_error "$package_type package build failed"
        return 1
    fi
}

# Build packages
BUILD_ERRORS=0

if [ "$PACKAGE_TYPES" = "all" ]; then
    TYPES_TO_BUILD=("deb" "rpm" "appimage")
else
    TYPES_TO_BUILD=("$PACKAGE_TYPES")
fi

if [ "$PARALLEL_BUILD" = true ] && [ "${#TYPES_TO_BUILD[@]}" -gt 1 ]; then
    log_info "Building packages in parallel..."
    
    # Build packages in parallel
    PIDS=()
    for package_type in "${TYPES_TO_BUILD[@]}"; do
        build_package "$package_type" &
        PIDS+=($!)
    done
    
    # Wait for all builds to complete
    for pid in "${PIDS[@]}"; do
        if ! wait "$pid"; then
            BUILD_ERRORS=$((BUILD_ERRORS + 1))
        fi
    done
else
    # Build packages sequentially
    for package_type in "${TYPES_TO_BUILD[@]}"; do
        if ! build_package "$package_type"; then
            BUILD_ERRORS=$((BUILD_ERRORS + 1))
        fi
    done
fi

# Summary
echo ""
log_info "Build Summary:"
log_info "=============="

if [ -d "$DIST_DIR" ]; then
    CREATED_FILES=()
    
    # Check for created packages
    for ext in "deb" "rpm" "AppImage" "tar.gz"; do
        while IFS= read -r -d '' file; do
            CREATED_FILES+=("$file")
        done < <(find "$DIST_DIR" -name "*.$ext" -type f -print0 2>/dev/null)
    done
    
    if [ ${#CREATED_FILES[@]} -gt 0 ]; then
        log_success "Created packages:"
        for file in "${CREATED_FILES[@]}"; do
            local size=$(du -h "$file" | cut -f1)
            log_success "  $(basename "$file") ($size)"
        done
    else
        log_warning "No packages were created"
    fi
else
    log_warning "Distribution directory not found"
fi

if [ $BUILD_ERRORS -eq 0 ]; then
    log_success "All package builds completed successfully!"
    echo ""
    log_info "Installation instructions:"
    log_info "  DEB: sudo dpkg -i <package>.deb"
    log_info "  RPM: sudo rpm -i <package>.rpm"
    log_info "  AppImage: chmod +x <package>.AppImage && ./<package>.AppImage"
    exit 0
else
    log_error "$BUILD_ERRORS package build(s) failed"
    exit 1
fi