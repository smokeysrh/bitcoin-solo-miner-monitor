#!/usr/bin/env python3
"""
Linux Dependency Resolver for Bitcoin Solo Miner Monitor

This script analyzes the application and system to determine the correct
dependencies for different Linux distributions.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DistributionDetector:
    """Detect the current Linux distribution and version."""
    
    def __init__(self):
        self.distro_info = self._detect_distribution()
    
    def _detect_distribution(self) -> Dict[str, str]:
        """Detect the current Linux distribution."""
        info = {
            'id': 'unknown',
            'version': 'unknown',
            'family': 'unknown',
            'package_manager': 'unknown'
        }
        
        # Try to read /etc/os-release
        os_release_path = Path('/etc/os-release')
        if os_release_path.exists():
            with open(os_release_path, 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        info['id'] = line.split('=')[1].strip().strip('"')
                    elif line.startswith('VERSION_ID='):
                        info['version'] = line.split('=')[1].strip().strip('"')
        
        # Determine distribution family and package manager
        if info['id'] in ['ubuntu', 'debian', 'linuxmint', 'pop']:
            info['family'] = 'debian'
            info['package_manager'] = 'apt'
        elif info['id'] in ['fedora', 'rhel', 'centos', 'rocky', 'almalinux']:
            info['family'] = 'redhat'
            info['package_manager'] = 'dnf' if info['id'] == 'fedora' else 'yum'
        elif info['id'] in ['opensuse', 'sles']:
            info['family'] = 'suse'
            info['package_manager'] = 'zypper'
        elif info['id'] in ['arch', 'manjaro']:
            info['family'] = 'arch'
            info['package_manager'] = 'pacman'
        
        return info
    
    def get_info(self) -> Dict[str, str]:
        """Get distribution information."""
        return self.distro_info.copy()


class DependencyResolver:
    """Resolve dependencies for different Linux distributions."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.detector = DistributionDetector()
        self.distro_info = self.detector.get_info()
        
        # Load dependency mappings
        self.dependency_mappings = self._load_dependency_mappings()
    
    def _load_dependency_mappings(self) -> Dict:
        """Load dependency mappings for different distributions."""
        return {
            'python': {
                'debian': {
                    'runtime': ['python3', 'python3-pip', 'python3-venv'],
                    'dev': ['python3-dev', 'python3-setuptools']
                },
                'redhat': {
                    'runtime': ['python3', 'python3-pip', 'python3-virtualenv'],
                    'dev': ['python3-devel', 'python3-setuptools']
                },
                'suse': {
                    'runtime': ['python3', 'python3-pip', 'python3-virtualenv'],
                    'dev': ['python3-devel', 'python3-setuptools']
                },
                'arch': {
                    'runtime': ['python', 'python-pip', 'python-virtualenv'],
                    'dev': ['python', 'python-setuptools']
                }
            },
            'nodejs': {
                'debian': {
                    'runtime': ['nodejs', 'npm'],
                    'dev': ['nodejs', 'npm', 'node-gyp']
                },
                'redhat': {
                    'runtime': ['nodejs', 'npm'],
                    'dev': ['nodejs', 'npm', 'nodejs-devel']
                },
                'suse': {
                    'runtime': ['nodejs', 'npm'],
                    'dev': ['nodejs', 'npm', 'nodejs-devel']
                },
                'arch': {
                    'runtime': ['nodejs', 'npm'],
                    'dev': ['nodejs', 'npm']
                }
            },
            'system': {
                'debian': {
                    'runtime': ['curl', 'wget', 'ca-certificates'],
                    'dev': ['build-essential', 'git']
                },
                'redhat': {
                    'runtime': ['curl', 'wget', 'ca-certificates'],
                    'dev': ['gcc', 'gcc-c++', 'make', 'git']
                },
                'suse': {
                    'runtime': ['curl', 'wget', 'ca-certificates'],
                    'dev': ['gcc', 'gcc-c++', 'make', 'git']
                },
                'arch': {
                    'runtime': ['curl', 'wget', 'ca-certificates'],
                    'dev': ['base-devel', 'git']
                }
            }
        }
    
    def _get_python_requirements(self) -> List[str]:
        """Parse Python requirements from requirements.txt."""
        requirements_file = self.project_root / 'requirements.txt'
        requirements = []
        
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before any version specifiers)
                        package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('[')[0]
                        requirements.append(package_name.strip())
        
        return requirements
    
    def _check_system_package_availability(self, packages: List[str]) -> Dict[str, bool]:
        """Check if system packages are available in the current distribution."""
        availability = {}
        package_manager = self.distro_info['package_manager']
        
        for package in packages:
            try:
                if package_manager == 'apt':
                    result = subprocess.run(['apt-cache', 'show', package], 
                                          capture_output=True, text=True)
                elif package_manager in ['dnf', 'yum']:
                    result = subprocess.run([package_manager, 'info', package], 
                                          capture_output=True, text=True)
                elif package_manager == 'zypper':
                    result = subprocess.run(['zypper', 'info', package], 
                                          capture_output=True, text=True)
                elif package_manager == 'pacman':
                    result = subprocess.run(['pacman', '-Si', package], 
                                          capture_output=True, text=True)
                else:
                    availability[package] = False
                    continue
                
                availability[package] = result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError):
                availability[package] = False
        
        return availability
    
    def get_runtime_dependencies(self) -> Dict[str, List[str]]:
        """Get runtime dependencies for the current distribution."""
        family = self.distro_info['family']
        dependencies = {
            'system': [],
            'python': [],
            'nodejs': []
        }
        
        # Get system dependencies
        if family in self.dependency_mappings['system']:
            dependencies['system'] = self.dependency_mappings['system'][family]['runtime']
        
        # Get Python dependencies
        if family in self.dependency_mappings['python']:
            dependencies['python'] = self.dependency_mappings['python'][family]['runtime']
        
        # Get Node.js dependencies
        if family in self.dependency_mappings['nodejs']:
            dependencies['nodejs'] = self.dependency_mappings['nodejs'][family]['runtime']
        
        return dependencies
    
    def get_build_dependencies(self) -> Dict[str, List[str]]:
        """Get build dependencies for the current distribution."""
        family = self.distro_info['family']
        dependencies = {
            'system': [],
            'python': [],
            'nodejs': []
        }
        
        # Get system build dependencies
        if family in self.dependency_mappings['system']:
            dependencies['system'] = self.dependency_mappings['system'][family]['dev']
        
        # Get Python build dependencies
        if family in self.dependency_mappings['python']:
            dependencies['python'] = self.dependency_mappings['python'][family]['dev']
        
        # Get Node.js build dependencies
        if family in self.dependency_mappings['nodejs']:
            dependencies['nodejs'] = self.dependency_mappings['nodejs'][family]['dev']
        
        return dependencies
    
    def generate_package_dependencies(self, package_type: str) -> Dict[str, any]:
        """Generate dependency specifications for package creation."""
        runtime_deps = self.get_runtime_dependencies()
        family = self.distro_info['family']
        
        # Combine all runtime dependencies
        all_deps = []
        for category, deps in runtime_deps.items():
            all_deps.extend(deps)
        
        # Format dependencies based on package type
        if package_type == 'deb':
            # Debian package format
            formatted_deps = []
            for dep in all_deps:
                if dep == 'python3':
                    formatted_deps.append('python3 (>= 3.11)')
                elif dep == 'nodejs':
                    formatted_deps.append('nodejs (>= 18.0)')
                else:
                    formatted_deps.append(dep)
            
            return {
                'depends': ', '.join(formatted_deps),
                'recommends': 'python3-venv, systemd',
                'suggests': 'nginx, sqlite3'
            }
        
        elif package_type == 'rpm':
            # RPM package format
            formatted_deps = []
            for dep in all_deps:
                if dep == 'python3':
                    formatted_deps.append('python3 >= 3.11')
                elif dep == 'nodejs':
                    formatted_deps.append('nodejs >= 18.0')
                else:
                    formatted_deps.append(dep)
            
            return {
                'requires': ', '.join(formatted_deps),
                'recommends': 'python3-virtualenv, systemd',
                'suggests': 'nginx, sqlite'
            }
        
        else:
            # Generic format
            return {
                'runtime': all_deps,
                'build': self.get_build_dependencies()
            }
    
    def validate_dependencies(self) -> Dict[str, any]:
        """Validate that all required dependencies are available."""
        runtime_deps = self.get_runtime_dependencies()
        validation_results = {
            'valid': True,
            'missing_packages': [],
            'warnings': [],
            'distribution_info': self.distro_info
        }
        
        # Check system package availability
        all_packages = []
        for category, packages in runtime_deps.items():
            all_packages.extend(packages)
        
        availability = self._check_system_package_availability(all_packages)
        
        for package, available in availability.items():
            if not available:
                validation_results['missing_packages'].append(package)
                validation_results['valid'] = False
        
        # Check Python requirements
        python_requirements = self._get_python_requirements()
        if len(python_requirements) > 20:
            validation_results['warnings'].append(
                f"Large number of Python dependencies ({len(python_requirements)}). "
                "Consider bundling dependencies or using virtual environments."
            )
        
        return validation_results
    
    def generate_install_script(self, package_type: str) -> str:
        """Generate installation script for the current distribution."""
        family = self.distro_info['family']
        package_manager = self.distro_info['package_manager']
        
        script_lines = [
            "#!/bin/bash",
            "# Auto-generated installation script for Bitcoin Solo Miner Monitor",
            f"# Distribution: {self.distro_info['id']} {self.distro_info['version']}",
            f"# Package Manager: {package_manager}",
            "",
            "set -e",
            "",
            "echo 'Installing Bitcoin Solo Miner Monitor dependencies...'",
            ""
        ]
        
        # Add package manager update
        if package_manager == 'apt':
            script_lines.extend([
                "# Update package lists",
                "sudo apt update",
                ""
            ])
        elif package_manager in ['dnf', 'yum']:
            script_lines.extend([
                "# Update package cache",
                f"sudo {package_manager} check-update || true",
                ""
            ])
        
        # Add dependency installation
        runtime_deps = self.get_runtime_dependencies()
        for category, packages in runtime_deps.items():
            if packages:
                script_lines.extend([
                    f"# Install {category} dependencies",
                    f"sudo {package_manager} install -y {' '.join(packages)}",
                    ""
                ])
        
        # Add Python package installation
        python_requirements = self._get_python_requirements()
        if python_requirements:
            script_lines.extend([
                "# Install Python packages",
                "python3 -m pip install --user " + " ".join(python_requirements),
                ""
            ])
        
        script_lines.extend([
            "echo 'Dependencies installed successfully!'",
            "echo 'You can now install the Bitcoin Solo Miner Monitor package.'"
        ])
        
        return "\n".join(script_lines)


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Linux Dependency Resolver')
    parser.add_argument('--project-root', default='.', 
                       help='Path to project root directory')
    parser.add_argument('--package-type', choices=['deb', 'rpm', 'generic'], 
                       default='generic', help='Package type to generate dependencies for')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate dependencies on current system')
    parser.add_argument('--generate-script', action='store_true',
                       help='Generate installation script')
    parser.add_argument('--output', help='Output file for generated content')
    
    args = parser.parse_args()
    
    resolver = DependencyResolver(args.project_root)
    
    if args.validate:
        print("Validating dependencies...")
        validation = resolver.validate_dependencies()
        print(json.dumps(validation, indent=2))
        
        if not validation['valid']:
            print("\nMissing packages detected. Install them with:")
            package_manager = validation['distribution_info']['package_manager']
            missing = ' '.join(validation['missing_packages'])
            print(f"sudo {package_manager} install {missing}")
            sys.exit(1)
    
    elif args.generate_script:
        script = resolver.generate_install_script(args.package_type)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(script)
            print(f"Installation script written to {args.output}")
        else:
            print(script)
    
    else:
        dependencies = resolver.generate_package_dependencies(args.package_type)
        output = json.dumps(dependencies, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Dependencies written to {args.output}")
        else:
            print(output)


if __name__ == '__main__':
    main()