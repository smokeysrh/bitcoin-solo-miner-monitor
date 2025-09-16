#!/usr/bin/env python3
# verify-checksums.py

import hashlib
import sys
from pathlib import Path

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def verify_checksums(checksums_file, base_dir=None):
    """Verify checksums from a SHA256SUMS file."""
    if base_dir is None:
        base_dir = Path(checksums_file).parent
    else:
        base_dir = Path(base_dir)
    
    checksums_path = Path(checksums_file)
    if not checksums_path.exists():
        print(f"Error: Checksums file not found: {checksums_file}")
        return False
    
    print(f"Verifying checksums from: {checksums_file}")
    print(f"Base directory: {base_dir}")
    print("")
    
    all_verified = True
    
    with open(checksums_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                expected_hash, filename = line.split('  ', 1)
                file_path = base_dir / filename
                
                if not file_path.exists():
                    print(f"❌ File not found: {filename}")
                    all_verified = False
                    continue
                
                actual_hash = calculate_sha256(file_path)
                
                if actual_hash == expected_hash:
                    print(f"✅ {filename}")
                else:
                    print(f"❌ {filename}")
                    print(f"   Expected: {expected_hash}")
                    print(f"   Actual:   {actual_hash}")
                    all_verified = False
                    
            except ValueError:
                print(f"Error: Invalid format on line {line_num}: {line}")
                all_verified = False
    
    print("")
    if all_verified:
        print("✅ All checksums verified successfully!")
        return True
    else:
        print("❌ Checksum verification failed!")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify-checksums.py <SHA256SUMS_file> [base_directory]")
        sys.exit(1)
    
    checksums_file = sys.argv[1]
    base_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = verify_checksums(checksums_file, base_dir)
    sys.exit(0 if success else 1)