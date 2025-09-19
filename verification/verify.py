#!/usr/bin/env python3
"""
Main Community Verification Script for Bitcoin Solo Miner Monitor

This is the main entry point for all community verification activities.
It provides a unified interface to all verification tools and processes.
"""

import argparse
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

try:
    # Import classes from the tools modules
    import importlib.util
    
    # Load community-verify module
    spec = importlib.util.spec_from_file_location("community_verify", Path(__file__).parent / "tools" / "community-verify.py")
    community_verify_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(community_verify_module)
    CommunityVerifier = community_verify_module.CommunityVerifier
    
    # Load compare-builds module
    spec = importlib.util.spec_from_file_location("compare_builds", Path(__file__).parent / "tools" / "compare-builds.py")
    compare_builds_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare_builds_module)
    BuildComparator = compare_builds_module.BuildComparator
    
    # Load github-integration module
    spec = importlib.util.spec_from_file_location("github_integration", Path(__file__).parent / "tools" / "github-integration.py")
    github_integration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(github_integration_module)
    GitHubVerificationIntegrator = github_integration_module.GitHubVerificationIntegrator
    
    # Load verification-dashboard module
    spec = importlib.util.spec_from_file_location("verification_dashboard", Path(__file__).parent / "tools" / "verification-dashboard.py")
    verification_dashboard_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verification_dashboard_module)
    VerificationDashboard = verification_dashboard_module.VerificationDashboard
    
except ImportError as e:
    print(f"Error importing verification tools: {e}")
    print("Please ensure all verification tools are properly installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error loading verification tools: {e}")
    print("Please check that all verification tool files exist and are valid Python files.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Bitcoin Solo Miner Monitor Community Verification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify a specific version
  python3 verify.py verify --version v0.1.0

  # Compare local build with community
  python3 verify.py compare --local SHA256SUMS --version v0.1.0

  # Generate verification dashboard
  python3 verify.py dashboard --format html --output dashboard.html

  # Sync verification data from GitHub
  python3 verify.py sync --token YOUR_GITHUB_TOKEN

For more information, see:
https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/verification/COMMUNITY_VERIFICATION_GUIDE.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify a release')
    verify_parser.add_argument('--version', '-v', required=True, help='Version to verify (e.g., v0.1.0)')
    verify_parser.add_argument('--method', '-m', choices=['checksum', 'reproducible', 'community', 'all'], 
                              default='all', help='Verification method')
    verify_parser.add_argument('--output', '-o', type=Path, help='Output file for report')
    verify_parser.add_argument('--repo', default='smokeysrh/bitcoin-solo-miner-monitor', 
                              help='GitHub repository')
    verify_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare local build with community')
    compare_parser.add_argument('--local', '-l', type=Path, required=True, 
                               help='Path to local SHA256SUMS file')
    compare_parser.add_argument('--version', '-v', required=True, help='Version to compare')
    compare_parser.add_argument('--output', '-o', type=Path, help='Output file for report')
    compare_parser.add_argument('--repo', default='smokeysrh/bitcoin-solo-miner-monitor', 
                               help='GitHub repository')
    compare_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Generate verification dashboard')
    dashboard_parser.add_argument('--format', choices=['markdown', 'html'], default='markdown',
                                 help='Output format')
    dashboard_parser.add_argument('--output', '-o', type=Path, help='Output file')
    dashboard_parser.add_argument('--verification-dir', type=Path, 
                                 help='Path to verification directory')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync verification data from GitHub')
    sync_parser.add_argument('--repo', default='smokeysrh/bitcoin-solo-miner-monitor',
                            help='GitHub repository')
    sync_parser.add_argument('--token', help='GitHub API token')
    sync_parser.add_argument('--output', '-o', type=Path, help='Output file for sync summary')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show verification status summary')
    status_parser.add_argument('--version', '-v', help='Show status for specific version')
    status_parser.add_argument('--verification-dir', type=Path, 
                              help='Path to verification directory')
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show detailed help')
    help_parser.add_argument('topic', nargs='?', 
                            choices=['verify', 'compare', 'dashboard', 'sync', 'status'],
                            help='Help topic')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'verify':
            handle_verify_command(args)
        elif args.command == 'compare':
            handle_compare_command(args)
        elif args.command == 'dashboard':
            handle_dashboard_command(args)
        elif args.command == 'sync':
            handle_sync_command(args)
        elif args.command == 'status':
            handle_status_command(args)
        elif args.command == 'help':
            handle_help_command(args)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def handle_verify_command(args):
    """Handle the verify command."""
    print(f"🔍 Starting verification for {args.version}")
    print(f"📋 Method: {args.method}")
    print()
    
    # Determine methods to run
    if args.method == "all":
        methods = ["checksum", "community"]
        # Only include reproducible build if we have git
        import subprocess
        if subprocess.run(["which", "git"], capture_output=True).returncode == 0:
            methods.append("reproducible")
    else:
        methods = [args.method]
    
    verifier = CommunityVerifier(args.version, args.repo)
    results = verifier.run_verification(methods)
    
    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        report = verifier.generate_report(args.output)
        if not args.output:
            print(report)
    
    # Exit with appropriate code
    if results["overall_status"] == "verified":
        print("\n✅ Verification completed successfully!")
        sys.exit(0)
    elif results["overall_status"] == "failed":
        print("\n❌ Verification failed!")
        sys.exit(1)
    else:
        print("\n⚠️ Verification completed with warnings.")
        sys.exit(2)

def handle_compare_command(args):
    """Handle the compare command."""
    print(f"🔍 Comparing local build with community for {args.version}")
    print(f"📁 Local file: {args.local}")
    print()
    
    comparator = BuildComparator(args.repo)
    result = comparator.compare_builds(args.local, args.version, args.output)
    
    if args.json:
        import json
        json_result = {k: v for k, v in result.items() if k != 'report'}
        print(json.dumps(json_result, indent=2))
    else:
        if not args.output:
            print(result['report'])
    
    # Exit with appropriate code based on risk level
    risk_level = result['analysis']['risk_level']
    if risk_level == 'high':
        print("\n❌ HIGH RISK: Significant differences detected!")
        sys.exit(1)
    elif risk_level == 'medium':
        print("\n⚠️ MEDIUM RISK: Some differences detected.")
        sys.exit(2)
    else:
        print("\n✅ LOW RISK: Builds appear consistent.")
        sys.exit(0)

def handle_dashboard_command(args):
    """Handle the dashboard command."""
    print(f"📊 Generating verification dashboard ({args.format} format)")
    
    dashboard = VerificationDashboard(args.verification_dir)
    result = dashboard.generate_dashboard(args.format, args.output)
    
    if not args.output:
        print(result)
    
    print(f"\n✅ Dashboard generated successfully!")

def handle_sync_command(args):
    """Handle the sync command."""
    print("🔄 Syncing verification data from GitHub issues")
    
    integrator = GitHubVerificationIntegrator(args.repo, args.token)
    result = integrator.sync_verification_data()
    
    print(result['summary'])
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(result['summary'])
        print(f"\nSummary saved to {args.output}")
    
    print(f"\n✅ Sync completed:")
    print(f"- Total issues processed: {result['total_issues']}")
    print(f"- Valid reports parsed: {result['total_reports']}")
    print(f"- Versions updated: {len(result['updated_versions'])}")

def handle_status_command(args):
    """Handle the status command."""
    dashboard = VerificationDashboard(args.verification_dir)
    verification_data = dashboard.load_verification_data()
    
    if args.version:
        # Show status for specific version
        if args.version in verification_data:
            data = verification_data[args.version]
            print(f"📋 Verification Status for {args.version}")
            print(f"Status: {data.get('verification_status', 'unknown').title()}")
            print(f"Verifications: {data.get('verification_count', 0)}")
            print(f"Security Notes: {len(data.get('security_notes', []))}")
            
            if data.get('verifications'):
                print("\nVerifications:")
                for v in data['verifications']:
                    print(f"  - {v.get('verifier', 'Unknown')}: {v.get('date', 'Unknown')[:10]}")
        else:
            print(f"❌ No verification data found for {args.version}")
            sys.exit(1)
    else:
        # Show overall status
        stats = dashboard.calculate_statistics(verification_data)
        
        print("📊 Community Verification Status Summary")
        print(f"Total Versions: {stats['total_versions']}")
        print(f"Verified: {stats['verified_versions']} 🟢")
        print(f"Pending: {stats['pending_versions']} 🟡")
        print(f"Failed: {stats['failed_versions']} 🔴")
        print(f"Unverified: {stats['unverified_versions']} ⚫")
        print(f"Total Verifications: {stats['total_verifications']}")
        print(f"Active Verifiers: {stats['total_verifiers']}")
        
        if stats['security_issues'] > 0:
            print(f"⚠️ Security Issues: {stats['security_issues']}")

def handle_help_command(args):
    """Handle the help command."""
    if not args.topic:
        print("""
🔍 Bitcoin Solo Miner Monitor Community Verification Tool

This tool helps community members verify the authenticity and integrity of releases
through multiple verification methods including checksum verification, reproducible
builds, and community consensus.

Available Commands:
  verify    - Verify a specific release
  compare   - Compare local build with community builds
  dashboard - Generate verification status dashboard
  sync      - Sync verification data from GitHub issues
  status    - Show verification status summary
  help      - Show this help or help for specific commands

For detailed help on a specific command:
  python3 verify.py help <command>

For complete documentation:
  https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/verification/COMMUNITY_VERIFICATION_GUIDE.md
        """)
    else:
        help_texts = {
            'verify': """
🔍 Verify Command

Verify the authenticity and integrity of a Bitcoin Solo Miner Monitor release
using multiple verification methods.

Usage:
  python3 verify.py verify --version v0.1.0 [options]

Options:
  --version, -v    Version to verify (required, e.g., v0.1.0)
  --method, -m     Verification method: checksum, reproducible, community, all (default: all)
  --output, -o     Output file for verification report
  --repo           GitHub repository (default: smokeysrh/bitcoin-solo-miner-monitor)
  --json           Output results in JSON format

Examples:
  # Verify latest release with all methods
  python3 verify.py verify --version v0.1.0

  # Only verify checksums
  python3 verify.py verify --version v0.1.0 --method checksum

  # Save report to file
  python3 verify.py verify --version v0.1.0 --output verification-report.md
            """,
            'compare': """
🔍 Compare Command

Compare your local build results with community-verified builds to detect
any inconsistencies or potential security issues.

Usage:
  python3 verify.py compare --local SHA256SUMS --version v0.1.0 [options]

Options:
  --local, -l      Path to local SHA256SUMS file (required)
  --version, -v    Version to compare against (required)
  --output, -o     Output file for comparison report
  --repo           GitHub repository (default: smokeysrh/bitcoin-solo-miner-monitor)
  --json           Output results in JSON format

Examples:
  # Compare local build with community
  python3 verify.py compare --local distribution/SHA256SUMS --version v0.1.0

  # Save comparison report
  python3 verify.py compare --local SHA256SUMS --version v0.1.0 --output comparison.md
            """,
            'dashboard': """
📊 Dashboard Command

Generate a comprehensive dashboard showing the verification status of all
releases, community participation statistics, and security information.

Usage:
  python3 verify.py dashboard [options]

Options:
  --format         Output format: markdown, html (default: markdown)
  --output, -o     Output file path
  --verification-dir  Path to verification directory

Examples:
  # Generate markdown dashboard
  python3 verify.py dashboard

  # Generate HTML dashboard
  python3 verify.py dashboard --format html --output dashboard.html

  # Use custom verification directory
  python3 verify.py dashboard --verification-dir /path/to/verification
            """,
            'sync': """
🔄 Sync Command

Synchronize verification data from GitHub issues to update community
verification status and statistics.

Usage:
  python3 verify.py sync [options]

Options:
  --repo           GitHub repository (default: smokeysrh/bitcoin-solo-miner-monitor)
  --token          GitHub API token (or set GITHUB_TOKEN environment variable)
  --output, -o     Output file for sync summary

Examples:
  # Sync verification data
  python3 verify.py sync --token YOUR_GITHUB_TOKEN

  # Sync and save summary
  python3 verify.py sync --output sync-summary.md

Note: GitHub token is required for API access. You can set the GITHUB_TOKEN
environment variable or use the --token option.
            """,
            'status': """
📋 Status Command

Show a quick summary of verification status for all versions or a specific version.

Usage:
  python3 verify.py status [options]

Options:
  --version, -v       Show status for specific version
  --verification-dir  Path to verification directory

Examples:
  # Show overall status
  python3 verify.py status

  # Show status for specific version
  python3 verify.py status --version v0.1.0

  # Use custom verification directory
  python3 verify.py status --verification-dir /path/to/verification
            """
        }
        
        print(help_texts.get(args.topic, f"No help available for '{args.topic}'"))

if __name__ == "__main__":
    main()