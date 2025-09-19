#!/usr/bin/env python3
"""
Quick Checksum Verification Tool for Bitcoin Solo Miner Monitor

This script provides a simple way to verify the integrity of downloaded
Bitcoin Solo Miner Monitor release files using SHA256 checksums.

Usage:
    python3 verify-checksums.py SHA256SUMS
    python3 verify-checksums.py --download v0.1.0
"""

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

def calculate_sha256(file_path):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest().lower()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

def download_file(url, filename):
    """Download a file with basic progress indication"""
    try:
        print(f"📥 Downloading {filename}...")
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r  Progress: {progress:.1f}%", end='', flush=True)
            
            print()  # New line after progress
            return True
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False

def verify_checksums(checksums_file):
    """Verify checksums from a SHA256SUMS file"""
    if not os.path.exists(checksums_file):
        print(f"❌ Checksums file not found: {checksums_file}")
        return False
    
    print(f"🔍 Verifying checksums from {checksums_file}")
    print("=" * 60)
    
    verified_count = 0
    failed_count = 0
    missing_count = 0
    
    try:
        with open(checksums_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse checksum line (format: "checksum  filename")
                if '  ' not in line:
                    print(f"⚠️  Line {line_num}: Invalid format, skipping")
                    continue
                
                expected_checksum, filename = line.split('  ', 1)
                expected_checksum = expected_checksum.lower()
                
                # Check if file exists
                if not os.path.exists(filename):
                    print(f"❌ {filename}: FILE NOT FOUND")
                    missing_count += 1
                    continue
                
                # Calculate actual checksum
                print(f"🔄 Verifying {filename}...", end=' ', flush=True)
                actual_checksum = calculate_sha256(filename)
                
                if actual_checksum is None:
                    print("ERROR")
                    failed_count += 1
                    continue
                
                # Compare checksums
                if actual_checksum == expected_checksum:
                    print("✅ VERIFIED")
                    verified_count += 1
                else:
                    print("❌ CHECKSUM MISMATCH")
                    print(f"   Expected: {expected_checksum}")
                    print(f"   Actual:   {actual_checksum}")
                    failed_count += 1
    
    except Exception as e:
        print(f"❌ Error reading checksums file: {e}")
        return False
    
    # Print summary
    print("=" * 60)
    print(f"📊 Verification Summary:")
    print(f"   ✅ Verified: {verified_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📁 Missing: {missing_count}")
    
    if failed_count == 0 and missing_count == 0 and verified_count > 0:
        print("🎉 All files verified successfully!")
        return True
    else:
        print("⚠️  Verification completed with issues!")
        if failed_count > 0:
            print("   DO NOT use files with checksum mismatches!")
        if missing_count > 0:
            print("   Some files are missing from the current directory.")
        return False

def download_and_verify(version):
    """Download release files and verify them"""
    repo_url = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
    
    # List of files to download and verify
    files_to_download = [
        f"BitcoinSoloMinerMonitor-{version.lstrip('v')}-Setup.exe",
        f"BitcoinSoloMinerMonitor-{version.lstrip('v')}.dmg",
        f"bitcoin-solo-miner-monitor_{version.lstrip('v')}_amd64.deb",
        f"bitcoin-solo-miner-monitor-{version.lstrip('v')}-1.x86_64.rpm",
        f"BitcoinSoloMinerMonitor-{version.lstrip('v')}-x86_64.AppImage"
    ]
    
    print(f"🚀 Downloading and verifying Bitcoin Solo Miner Monitor {version}")
    print("=" * 60)
    
    # Download checksums file first
    checksums_url = f"{repo_url}/releases/download/{version}/SHA256SUMS"
    if not download_file(checksums_url, "SHA256SUMS"):
        return False
    
    # Parse checksums to see which files are actually available
    available_files = set()
    try:
        with open("SHA256SUMS", 'r') as f:
            for line in f:
                line = line.strip()
                if line and '  ' in line:
                    _, filename = line.split('  ', 1)
                    available_files.add(filename)
    except Exception as e:
        print(f"❌ Error reading SHA256SUMS: {e}")
        return False
    
    print(f"📋 Found {len(available_files)} files in release")
    
    # Download available files
    downloaded_files = []
    for filename in available_files:
        file_url = f"{repo_url}/releases/download/{version}/{filename}"
        if download_file(file_url, filename):
            downloaded_files.append(filename)
        else:
            print(f"⚠️  Failed to download {filename}, continuing...")
    
    print(f"📥 Downloaded {len(downloaded_files)} files")
    print()
    
    # Verify checksums
    return verify_checksums("SHA256SUMS")

def main():
    parser = argparse.ArgumentParser(
        description="Verify Bitcoin Solo Miner Monitor release file checksums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify files in current directory using existing SHA256SUMS
  python3 verify-checksums.py SHA256SUMS
  
  # Download and verify a specific release
  python3 verify-checksums.py --download v0.1.0
  
  # Verify specific files
  python3 verify-checksums.py --files installer.exe installer.dmg
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "checksums_file",
        nargs='?',
        help="Path to SHA256SUMS file"
    )
    group.add_argument(
        "--download",
        metavar="VERSION",
        help="Download and verify specific version (e.g., v0.1.0)"
    )
    
    parser.add_argument(
        "--files",
        nargs='+',
        help="Specific files to verify (requires checksums_file)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.download:
            success = download_and_verify(args.download)
        else:
            if args.files:
                # Create temporary checksums file with only specified files
                temp_checksums = "temp_checksums.txt"
                try:
                    with open(args.checksums_file, 'r') as src:
                        with open(temp_checksums, 'w') as dst:
                            for line in src:
                                line = line.strip()
                                if line and '  ' in line:
                                    _, filename = line.split('  ', 1)
                                    if filename in args.files:
                                        dst.write(line + '\n')
                    
                    success = verify_checksums(temp_checksums)
                    os.remove(temp_checksums)
                except Exception as e:
                    print(f"❌ Error processing files: {e}")
                    success = False
            else:
                success = verify_checksums(args.checksums_file)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()