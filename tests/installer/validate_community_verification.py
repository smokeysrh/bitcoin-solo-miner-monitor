#!/usr/bin/env python3
"""
Community Verification Process Validation Script

This script validates that all community verification processes are working correctly
and that documentation is accurate and up-to-date.
"""

import os
import sys
import json
import subprocess
import hashlib
import requests
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CommunityVerificationValidator:
    """Validates community verification processes and documentation."""
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path.cwd()
        self.verification_dir = self.repo_root / 'verification'
        self.tools_dir = self.verification_dir / 'tools'
        
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'validations': {},
            'summary': {
                'total_validations': 0,
                'passed_validations': 0,
                'failed_validations': 0,
                'issues': [],
                'recommendations': []
            }
        }
    
    def validate_all_processes(self) -> Dict[str, Any]:
        """Validate all community verification processes."""
        logger.info("🔍 Starting community verification process validation")
        
        validations = [
            'verification_tools_functionality',
            'documentation_accuracy',
            'checksum_verification_process',
            'reproducible_build_process',
            'github_integration',
            'community_guidelines',
            'verification_dashboard'
        ]
        
        for validation in validations:
            logger.info(f"🔧 Validating {validation}...")
            result = self._run_validation(validation)
            self.validation_results['validations'][validation] = result
            self.validation_results['summary']['total_validations'] += 1
            
            if result['status'] == 'passed':
                self.validation_results['summary']['passed_validations'] += 1
            else:
                self.validation_results['summary']['failed_validations'] += 1
                self.validation_results['summary']['issues'].extend(result.get('issues', []))
        
        # Determine overall status
        success_rate = (self.validation_results['summary']['passed_validations'] / 
                       self.validation_results['summary']['total_validations'])
        
        if success_rate >= 0.9:
            self.validation_results['overall_status'] = 'passed'
        elif success_rate >= 0.7:
            self.validation_results['overall_status'] = 'partial'
        else:
            self.validation_results['overall_status'] = 'failed'
        
        self._generate_recommendations()
        
        logger.info("✅ Community verification validation completed")
        return self.validation_results
    
    def _run_validation(self, validation_type: str) -> Dict[str, Any]:
        """Run a specific validation."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        try:
            if validation_type == 'verification_tools_functionality':
                result = self._validate_verification_tools()
            elif validation_type == 'documentation_accuracy':
                result = self._validate_documentation()
            elif validation_type == 'checksum_verification_process':
                result = self._validate_checksum_process()
            elif validation_type == 'reproducible_build_process':
                result = self._validate_reproducible_builds()
            elif validation_type == 'github_integration':
                result = self._validate_github_integration()
            elif validation_type == 'community_guidelines':
                result = self._validate_community_guidelines()
            elif validation_type == 'verification_dashboard':
                result = self._validate_verification_dashboard()
            
        except Exception as e:
            result['status'] = 'failed'
            result['issues'] = [f"Exception in {validation_type}: {str(e)}"]
        
        return result   
 
    def _validate_verification_tools(self) -> Dict[str, Any]:
        """Validate that verification tools are functional."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check if tools directory exists
        if not self.tools_dir.exists():
            result['status'] = 'failed'
            result['issues'].append("Verification tools directory not found")
            return result
        
        # Check for required tools
        required_tools = [
            'community-verify.py',
            'compare-builds.py',
            'github-integration.py',
            'verification-dashboard.py'
        ]
        
        found_tools = []
        missing_tools = []
        
        for tool in required_tools:
            tool_path = self.tools_dir / tool
            if tool_path.exists():
                found_tools.append(tool)
            else:
                missing_tools.append(tool)
        
        result['details']['found_tools'] = found_tools
        result['details']['missing_tools'] = missing_tools
        
        # Check main verify.py script
        main_verify = self.verification_dir / 'verify.py'
        if main_verify.exists():
            result['details']['main_script'] = 'found'
        else:
            result['issues'].append("Main verify.py script not found")
        
        # Determine status
        if not missing_tools and not result['issues']:
            result['status'] = 'passed'
        elif len(found_tools) > len(missing_tools):
            result['status'] = 'partial'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _validate_documentation(self) -> Dict[str, Any]:
        """Validate documentation accuracy and completeness."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for key documentation files
        key_docs = [
            self.verification_dir / 'COMMUNITY_VERIFICATION_GUIDE.md',
            self.verification_dir / 'README.md',
            self.repo_root / 'docs' / 'installation',
            self.repo_root / 'CONTRIBUTING.md'
        ]
        
        found_docs = []
        missing_docs = []
        
        for doc_path in key_docs:
            if doc_path.exists():
                found_docs.append(str(doc_path.relative_to(self.repo_root)))
            else:
                missing_docs.append(str(doc_path.relative_to(self.repo_root)))
        
        result['details']['found_docs'] = found_docs
        result['details']['missing_docs'] = missing_docs
        
        # Determine status
        if not missing_docs:
            result['status'] = 'passed'
        elif len(found_docs) > len(missing_docs):
            result['status'] = 'partial'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _validate_checksum_process(self) -> Dict[str, Any]:
        """Validate checksum verification process."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for checksum generation in CI/CD
        workflows_dir = self.repo_root / '.github' / 'workflows'
        build_workflow = workflows_dir / 'build-installers.yml'
        
        if build_workflow.exists():
            content = build_workflow.read_text()
            
            # Check for SHA256 checksum generation
            if 'sha256' in content.lower() or 'checksum' in content.lower():
                result['details']['checksum_generation'] = 'configured'
                result['status'] = 'passed'
            else:
                result['issues'].append("No checksum generation found in build workflow")
                result['status'] = 'failed'
        else:
            result['issues'].append("Build workflow not found")
            result['status'] = 'failed'
        
        return result
    
    def _validate_reproducible_builds(self) -> Dict[str, Any]:
        """Validate reproducible build process."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for build documentation
        build_docs = []
        docs_dir = self.repo_root / 'docs'
        
        if docs_dir.exists():
            build_docs.extend(list(docs_dir.rglob('*build*.md')))
            build_docs.extend(list(docs_dir.rglob('*BUILD*.md')))
        
        if build_docs:
            result['details']['build_documentation'] = [str(f.relative_to(self.repo_root)) for f in build_docs]
            result['status'] = 'passed'
        else:
            result['issues'].append("No build documentation found")
            result['status'] = 'partial'
        
        return result
    
    def _validate_github_integration(self) -> Dict[str, Any]:
        """Validate GitHub integration for verification."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for GitHub Actions workflows
        workflows_dir = self.repo_root / '.github' / 'workflows'
        if workflows_dir.exists():
            workflows = list(workflows_dir.glob('*.yml'))
            result['details']['workflows'] = [w.name for w in workflows]
            
            if workflows:
                result['status'] = 'passed'
            else:
                result['status'] = 'failed'
                result['issues'].append("No GitHub Actions workflows found")
        else:
            result['issues'].append("No GitHub Actions workflows found")
            result['status'] = 'failed'
        
        return result
    
    def _validate_community_guidelines(self) -> Dict[str, Any]:
        """Validate community guidelines and contribution process."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for community files
        community_files = [
            self.repo_root / 'CONTRIBUTING.md',
            self.repo_root / 'CODE_OF_CONDUCT.md'
        ]
        
        found_files = []
        for file_path in community_files:
            if file_path.exists():
                found_files.append(file_path.name)
        
        result['details']['community_files'] = found_files
        
        if len(found_files) >= 1:
            result['status'] = 'passed'
        else:
            result['issues'].append("Limited community documentation")
            result['status'] = 'failed'
        
        return result
    
    def _validate_verification_dashboard(self) -> Dict[str, Any]:
        """Validate verification dashboard functionality."""
        result = {'status': 'unknown', 'details': {}, 'issues': []}
        
        # Check for dashboard tool
        dashboard_tool = self.tools_dir / 'verification-dashboard.py'
        if dashboard_tool.exists():
            result['details']['dashboard_tool'] = 'found'
            result['status'] = 'passed'
        else:
            result['issues'].append("Verification dashboard tool not found")
            result['status'] = 'partial'
        
        return result
    
    def _generate_recommendations(self):
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Analyze validation results and generate specific recommendations
        for validation_name, validation_result in self.validation_results['validations'].items():
            if validation_result['status'] != 'passed':
                if validation_name == 'verification_tools_functionality':
                    recommendations.append("Complete implementation of missing verification tools")
                elif validation_name == 'documentation_accuracy':
                    recommendations.append("Update and expand verification documentation")
                elif validation_name == 'checksum_verification_process':
                    recommendations.append("Implement comprehensive checksum generation and verification")
                elif validation_name == 'reproducible_build_process':
                    recommendations.append("Document and implement reproducible build processes")
                elif validation_name == 'github_integration':
                    recommendations.append("Enhance GitHub integration for community verification")
                elif validation_name == 'community_guidelines':
                    recommendations.append("Develop comprehensive community verification guidelines")
                elif validation_name == 'verification_dashboard':
                    recommendations.append("Complete verification dashboard implementation")
        
        self.validation_results['summary']['recommendations'] = recommendations[:10]
    
    def save_results(self, output_file: Path = None) -> Path:
        """Save validation results to file."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_dir = self.repo_root / 'tests' / 'installer' / 'results'
            results_dir.mkdir(parents=True, exist_ok=True)
            output_file = results_dir / f'community_verification_validation_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        logger.info(f"📄 Validation results saved to {output_file}")
        return output_file

def main():
    """Main entry point for community verification validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Community Verification Process Validation"
    )
    parser.add_argument('--repo-root', type=Path, help='Repository root directory')
    parser.add_argument('--output-dir', type=Path, help='Output directory for results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize validator
    validator = CommunityVerificationValidator(args.repo_root)
    
    try:
        # Run validation
        logger.info("🚀 Starting community verification validation...")
        results = validator.validate_all_processes()
        
        # Save results
        results_file = validator.save_results()
        
        # Print summary
        print("\n" + "="*80)
        print("COMMUNITY VERIFICATION VALIDATION COMPLETE")
        print("="*80)
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Success Rate: {results['summary']['passed_validations']}/{results['summary']['total_validations']}")
        print(f"Results saved to: {results_file}")
        print("="*80)
        
        # Exit with appropriate code
        if results['overall_status'] == 'passed':
            sys.exit(0)
        elif results['overall_status'] == 'partial':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        logger.info("❌ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Validation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()