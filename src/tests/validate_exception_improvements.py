"""
Validation script for exception handling improvements.

This script validates that broad exception handling has been replaced
with specific exceptions and structured logging.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def find_broad_exceptions(file_path: Path) -> List[Tuple[int, str]]:
    """Find instances of broad exception handling in a file."""
    broad_exceptions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Look for broad exception patterns
            if re.search(r'except\s+Exception\s+as\s+\w+:', line):
                broad_exceptions.append((line_num, line.strip()))
            elif re.search(r'except\s*:', line):
                broad_exceptions.append((line_num, line.strip()))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return broad_exceptions


def find_specific_exceptions(file_path: Path) -> List[Tuple[int, str]]:
    """Find instances of specific exception handling in a file."""
    specific_exceptions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Look for specific exception patterns
            if re.search(r'except\s+\w+Error\s+as\s+\w+:', line):
                specific_exceptions.append((line_num, line.strip()))
            elif re.search(r'except\s+\w+Exception\s+as\s+\w+:', line):
                specific_exceptions.append((line_num, line.strip()))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return specific_exceptions


def check_structured_logging_imports(file_path: Path) -> bool:
    """Check if file imports structured logging utilities."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return 'structured_logging' in content or 'get_logger' in content
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False


def check_custom_exception_imports(file_path: Path) -> bool:
    """Check if file imports custom exceptions."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return 'src.backend.exceptions' in content
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False


def validate_file(file_path: Path) -> Dict[str, any]:
    """Validate exception handling improvements in a single file."""
    result = {
        'file': str(file_path),
        'broad_exceptions': find_broad_exceptions(file_path),
        'specific_exceptions': find_specific_exceptions(file_path),
        'has_structured_logging': check_structured_logging_imports(file_path),
        'has_custom_exceptions': check_custom_exception_imports(file_path),
        'improvement_score': 0
    }
    
    # Calculate improvement score
    broad_count = len(result['broad_exceptions'])
    specific_count = len(result['specific_exceptions'])
    
    if broad_count == 0 and specific_count > 0:
        result['improvement_score'] = 100
    elif broad_count > 0 and specific_count > 0:
        result['improvement_score'] = int((specific_count / (broad_count + specific_count)) * 100)
    elif broad_count == 0 and specific_count == 0:
        result['improvement_score'] = 50  # No exceptions at all
    else:
        result['improvement_score'] = 0  # Only broad exceptions
    
    return result


def main():
    """Main validation function."""
    print("🔍 Validating exception handling improvements...")
    
    # Files to check (the ones we modified)
    files_to_check = [
        Path('src/main.py'),
        Path('src/backend/models/miner_factory.py'),
        Path('src/backend/models/magic_miner.py'),
        Path('src/backend/services/miner_manager.py'),
        Path('src/backend/utils/config_validator.py'),
    ]
    
    total_score = 0
    results = []
    
    for file_path in files_to_check:
        if file_path.exists():
            result = validate_file(file_path)
            results.append(result)
            total_score += result['improvement_score']
            
            print(f"\n📁 {file_path}")
            print(f"   Broad exceptions: {len(result['broad_exceptions'])}")
            print(f"   Specific exceptions: {len(result['specific_exceptions'])}")
            print(f"   Structured logging: {'✅' if result['has_structured_logging'] else '❌'}")
            print(f"   Custom exceptions: {'✅' if result['has_custom_exceptions'] else '❌'}")
            print(f"   Improvement score: {result['improvement_score']}%")
            
            # Show remaining broad exceptions
            if result['broad_exceptions']:
                print("   ⚠️  Remaining broad exceptions:")
                for line_num, line in result['broad_exceptions'][:3]:  # Show first 3
                    print(f"      Line {line_num}: {line}")
                if len(result['broad_exceptions']) > 3:
                    print(f"      ... and {len(result['broad_exceptions']) - 3} more")
        else:
            print(f"\n❌ File not found: {file_path}")
    
    # Calculate overall score
    if results:
        overall_score = total_score // len(results)
        print(f"\n📊 Overall improvement score: {overall_score}%")
        
        if overall_score >= 80:
            print("🎉 Excellent! Exception handling has been significantly improved.")
        elif overall_score >= 60:
            print("👍 Good progress on exception handling improvements.")
        elif overall_score >= 40:
            print("📈 Some improvements made, but more work needed.")
        else:
            print("⚠️  Limited improvements detected. More work needed.")
    
    # Check if custom exception module exists
    exceptions_file = Path('src/backend/exceptions.py')
    if exceptions_file.exists():
        print(f"\n✅ Custom exceptions module created: {exceptions_file}")
    else:
        print(f"\n❌ Custom exceptions module not found: {exceptions_file}")
    
    # Check if structured logging module exists
    logging_file = Path('src/backend/utils/structured_logging.py')
    if logging_file.exists():
        print(f"✅ Structured logging module created: {logging_file}")
    else:
        print(f"❌ Structured logging module not found: {logging_file}")
    
    print("\n🔧 Exception handling improvement validation complete!")


if __name__ == "__main__":
    main()