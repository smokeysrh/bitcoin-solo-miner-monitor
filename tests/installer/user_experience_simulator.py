#!/usr/bin/env python3
"""
User Experience Testing Simulator for Bitcoin Solo Miner Monitor
Simulates non-technical user interactions with installers and application
"""

import os
import sys
import json
import time
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
import logging
import random
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserPersona:
    """Represents different types of users with varying technical skills"""
    
    def __init__(self, name: str, technical_level: str, behaviors: Dict):
        self.name = name
        self.technical_level = technical_level  # "beginner", "intermediate", "advanced"
        self.behaviors = behaviors
        
    def get_behavior(self, action: str) -> Dict:
        """Get behavior pattern for a specific action"""
        return self.behaviors.get(action, {})

class UserExperienceSimulator:
    """Simulates user experience testing with different user personas"""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.test_results_dir = self.project_root / "tests" / "installer" / "ux_results"
        self.test_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Define user personas
        self.user_personas = {
            "novice_miner": UserPersona(
                name="Novice Bitcoin Miner",
                technical_level="beginner",
                behaviors={
                    "installation": {
                        "reads_instructions": False,
                        "uses_default_settings": True,
                        "patience_seconds": 30,
                        "likely_to_quit_on_error": True,
                        "checks_antivirus_warnings": False
                    },
                    "first_run": {
                        "skips_setup_wizard": False,
                        "uses_simple_mode": True,
                        "reads_tooltips": False,
                        "patience_for_discovery": 60
                    },
                    "configuration": {
                        "changes_advanced_settings": False,
                        "uses_auto_discovery": True,
                        "sets_custom_paths": False
                    }
                }
            ),
            "experienced_miner": UserPersona(
                name="Experienced Bitcoin Miner",
                technical_level="intermediate",
                behaviors={
                    "installation": {
                        "reads_instructions": True,
                        "uses_default_settings": False,
                        "patience_seconds": 120,
                        "likely_to_quit_on_error": False,
                        "checks_antivirus_warnings": True
                    },
                    "first_run": {
                        "skips_setup_wizard": False,
                        "uses_simple_mode": False,
                        "reads_tooltips": True,
                        "patience_for_discovery": 180
                    },
                    "configuration": {
                        "changes_advanced_settings": True,
                        "uses_auto_discovery": True,
                        "sets_custom_paths": True
                    }
                }
            ),
            "tech_savvy_user": UserPersona(
                name="Tech-Savvy User",
                technical_level="advanced",
                behaviors={
                    "installation": {
                        "reads_instructions": True,
                        "uses_default_settings": False,
                        "patience_seconds": 300,
                        "likely_to_quit_on_error": False,
                        "checks_antivirus_warnings": True
                    },
                    "first_run": {
                        "skips_setup_wizard": True,
                        "uses_simple_mode": False,
                        "reads_tooltips": False,
                        "patience_for_discovery": 300
                    },
                    "configuration": {
                        "changes_advanced_settings": True,
                        "uses_auto_discovery": False,
                        "sets_custom_paths": True
                    }
                }
            )
        }
        
        # Initialize test session
        self.test_session = {
            "session_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "platform": platform.system().lower(),
            "user_tests": [],
            "summary": {
                "total_personas": len(self.user_personas),
                "successful_installations": 0,
                "successful_first_runs": 0,
                "user_satisfaction_score": 0.0,
                "average_installation_time": 0.0,
                "common_pain_points": []
            }
        }
    
    def simulate_installation_experience(self, installer_path: Path, persona: UserPersona) -> Dict:
        """Simulate installation experience for a specific user persona"""
        logger.info(f"🎭 Simulating installation for {persona.name}")
        
        start_time = time.time()
        experience = {
            "persona": persona.name,
            "technical_level": persona.technical_level,
            "installer_file": installer_path.name,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "steps": [],
            "success": False,
            "satisfaction_score": 0,
            "pain_points": [],
            "positive_points": [],
            "total_time_seconds": 0
        }
        
        try:
            # Step 1: Download and file handling
            self.simulate_download_experience(experience, persona)
            
            # Step 2: Security warnings handling
            self.simulate_security_warnings(experience, persona, installer_path)
            
            # Step 3: Installation process
            self.simulate_installation_process(experience, persona, installer_path)
            
            # Step 4: First launch
            self.simulate_first_launch(experience, persona)
            
            # Step 5: Initial configuration
            self.simulate_initial_configuration(experience, persona)
            
            # Calculate overall experience
            experience["total_time_seconds"] = time.time() - start_time
            experience["success"] = len([s for s in experience["steps"] if s.get("success", False)]) >= 3
            experience["satisfaction_score"] = self.calculate_satisfaction_score(experience, persona)
            
        except Exception as e:
            logger.error(f"Error simulating experience for {persona.name}: {e}")
            experience["error"] = str(e)
            
        experience["end_time"] = datetime.now(timezone.utc).isoformat()
        return experience
    
    def simulate_download_experience(self, experience: Dict, persona: UserPersona):
        """Simulate the download and file handling experience"""
        step = {
            "step_name": "download_and_file_handling",
            "start_time": time.time(),
            "success": True,
            "details": {}
        }
        
        # Simulate download confusion for beginners
        if persona.technical_level == "beginner":
            # Novice users might be confused by multiple download options
            if random.random() < 0.3:  # 30% chance of confusion
                step["details"]["confusion"] = "Multiple download options confusing"
                experience["pain_points"].append("Too many download options")
                step["duration_seconds"] = random.uniform(60, 180)  # Takes longer due to confusion
            else:
                step["duration_seconds"] = random.uniform(10, 30)
        else:
            step["duration_seconds"] = random.uniform(5, 15)
            
        # Check if user notices file size
        if persona.behaviors["installation"]["reads_instructions"]:
            step["details"]["noticed_file_size"] = True
            experience["positive_points"].append("User noticed reasonable file size")
        
        step["end_time"] = step["start_time"] + step["duration_seconds"]
        experience["steps"].append(step)
    
    def simulate_security_warnings(self, experience: Dict, persona: UserPersona, installer_path: Path):
        """Simulate handling of security warnings"""
        step = {
            "step_name": "security_warnings",
            "start_time": time.time(),
            "success": False,
            "details": {}
        }
        
        # Simulate Windows "Unknown Publisher" warning
        if installer_path.suffix.lower() == ".exe":
            step["details"]["warning_type"] = "unknown_publisher"
            
            if persona.behaviors["installation"]["checks_antivirus_warnings"]:
                # User checks warnings and proceeds carefully
                step["duration_seconds"] = random.uniform(30, 90)
                step["success"] = True
                step["details"]["user_action"] = "researched_warning_and_proceeded"
                experience["positive_points"].append("User properly handled security warning")
            else:
                # Novice user might be scared off
                if persona.technical_level == "beginner" and random.random() < 0.4:  # 40% chance
                    step["duration_seconds"] = random.uniform(10, 30)
                    step["success"] = False
                    step["details"]["user_action"] = "scared_off_by_warning"
                    experience["pain_points"].append("Security warning scared user away")
                else:
                    step["duration_seconds"] = random.uniform(5, 20)
                    step["success"] = True
                    step["details"]["user_action"] = "clicked_through_warning"
        
        # Simulate antivirus warnings
        if random.random() < 0.6:  # 60% chance of antivirus warning for mining software
            step["details"]["antivirus_warning"] = True
            
            if persona.behaviors["installation"]["checks_antivirus_warnings"]:
                step["details"]["antivirus_action"] = "added_exception"
                experience["positive_points"].append("User successfully handled antivirus warning")
            else:
                if persona.technical_level == "beginner":
                    step["details"]["antivirus_action"] = "confused_by_warning"
                    experience["pain_points"].append("Antivirus warning caused confusion")
                    step["duration_seconds"] += random.uniform(60, 180)
        
        step["end_time"] = step["start_time"] + step.get("duration_seconds", 30)
        experience["steps"].append(step)
    
    def simulate_installation_process(self, experience: Dict, persona: UserPersona, installer_path: Path):
        """Simulate the actual installation process"""
        step = {
            "step_name": "installation_process",
            "start_time": time.time(),
            "success": True,
            "details": {}
        }
        
        # Simulate installation time based on installer type
        base_time = {
            ".exe": random.uniform(30, 90),
            ".dmg": random.uniform(15, 45),
            ".deb": random.uniform(10, 30),
            ".rpm": random.uniform(10, 30),
            ".appimage": random.uniform(5, 15)
        }.get(installer_path.suffix.lower(), 30)
        
        # Adjust time based on user behavior
        if persona.behaviors["installation"]["uses_default_settings"]:
            step["duration_seconds"] = base_time
            step["details"]["settings"] = "default"
        else:
            step["duration_seconds"] = base_time * random.uniform(1.5, 3.0)  # Takes longer to customize
            step["details"]["settings"] = "customized"
            experience["positive_points"].append("User customized installation settings")
        
        # Simulate potential issues
        if random.random() < 0.1:  # 10% chance of installation issue
            step["details"]["issue"] = "temporary_installation_error"
            step["duration_seconds"] += random.uniform(30, 120)
            
            if persona.behaviors["installation"]["likely_to_quit_on_error"]:
                if random.random() < 0.5:  # 50% chance novice quits
                    step["success"] = False
                    step["details"]["user_action"] = "quit_on_error"
                    experience["pain_points"].append("User quit due to installation error")
                else:
                    step["details"]["user_action"] = "retried_installation"
            else:
                step["details"]["user_action"] = "troubleshot_and_continued"
                experience["positive_points"].append("User successfully troubleshot installation issue")
        
        # Check patience threshold
        patience = persona.behaviors["installation"]["patience_seconds"]
        if step["duration_seconds"] > patience:
            if persona.technical_level == "beginner":
                step["success"] = False
                step["details"]["timeout_reason"] = "exceeded_patience"
                experience["pain_points"].append("Installation took too long for user patience")
        
        step["end_time"] = step["start_time"] + step["duration_seconds"]
        experience["steps"].append(step)
    
    def simulate_first_launch(self, experience: Dict, persona: UserPersona):
        """Simulate first application launch experience"""
        step = {
            "step_name": "first_launch",
            "start_time": time.time(),
            "success": True,
            "details": {}
        }
        
        # Simulate finding and launching the application
        if persona.technical_level == "beginner":
            # Novice might have trouble finding the application
            if random.random() < 0.2:  # 20% chance of confusion
                step["details"]["finding_app"] = "confused_about_location"
                experience["pain_points"].append("User had trouble finding installed application")
                step["duration_seconds"] = random.uniform(60, 180)
            else:
                step["duration_seconds"] = random.uniform(10, 30)
        else:
            step["duration_seconds"] = random.uniform(5, 15)
        
        # Simulate application startup time
        startup_time = random.uniform(5, 20)
        step["duration_seconds"] += startup_time
        step["details"]["startup_time_seconds"] = startup_time
        
        # Check if startup time exceeds user patience
        if startup_time > 15 and persona.technical_level == "beginner":
            step["details"]["startup_patience"] = "exceeded"
            experience["pain_points"].append("Application startup took too long")
        
        # Simulate first-run setup wizard
        if not persona.behaviors["first_run"]["skips_setup_wizard"]:
            wizard_time = random.uniform(30, 120)
            step["duration_seconds"] += wizard_time
            step["details"]["setup_wizard_time"] = wizard_time
            
            if persona.behaviors["first_run"]["uses_simple_mode"]:
                step["details"]["setup_mode"] = "simple"
                experience["positive_points"].append("User successfully used simple setup mode")
            else:
                step["details"]["setup_mode"] = "advanced"
        else:
            step["details"]["setup_wizard"] = "skipped"
        
        step["end_time"] = step["start_time"] + step["duration_seconds"]
        experience["steps"].append(step)
    
    def simulate_initial_configuration(self, experience: Dict, persona: UserPersona):
        """Simulate initial configuration and miner discovery"""
        step = {
            "step_name": "initial_configuration",
            "start_time": time.time(),
            "success": True,
            "details": {}
        }
        
        # Simulate miner discovery process
        if persona.behaviors["configuration"]["uses_auto_discovery"]:
            discovery_time = random.uniform(10, 60)
            step["details"]["discovery_method"] = "automatic"
            step["details"]["discovery_time"] = discovery_time
            
            # Simulate discovery success rate
            if random.random() < 0.8:  # 80% success rate for auto-discovery
                step["details"]["miners_found"] = random.randint(1, 3)
                experience["positive_points"].append("Auto-discovery successfully found miners")
            else:
                step["details"]["miners_found"] = 0
                experience["pain_points"].append("Auto-discovery failed to find miners")
                
                # User might try manual configuration
                if persona.technical_level != "beginner":
                    step["details"]["fallback_to_manual"] = True
                    discovery_time += random.uniform(60, 180)
        else:
            # Manual configuration
            discovery_time = random.uniform(60, 300)
            step["details"]["discovery_method"] = "manual"
            step["details"]["discovery_time"] = discovery_time
            
            if persona.technical_level == "advanced":
                step["details"]["miners_configured"] = random.randint(1, 5)
                experience["positive_points"].append("User successfully configured miners manually")
            else:
                # Intermediate users might struggle with manual config
                if random.random() < 0.3:  # 30% chance of difficulty
                    experience["pain_points"].append("Manual configuration was challenging")
        
        step["duration_seconds"] = discovery_time
        
        # Check patience for discovery process
        patience = persona.behaviors["first_run"]["patience_for_discovery"]
        if discovery_time > patience:
            step["success"] = False
            step["details"]["timeout_reason"] = "discovery_took_too_long"
            experience["pain_points"].append("Miner discovery process exceeded user patience")
        
        step["end_time"] = step["start_time"] + step["duration_seconds"]
        experience["steps"].append(step)
    
    def calculate_satisfaction_score(self, experience: Dict, persona: UserPersona) -> float:
        """Calculate user satisfaction score based on experience"""
        base_score = 5.0  # Start with neutral score
        
        # Positive factors
        positive_points = len(experience["positive_points"])
        base_score += positive_points * 0.5
        
        # Negative factors
        pain_points = len(experience["pain_points"])
        base_score -= pain_points * 0.8
        
        # Time factor - penalize if took too long
        total_time = experience["total_time_seconds"]
        expected_time = {
            "beginner": 300,    # 5 minutes
            "intermediate": 180, # 3 minutes
            "advanced": 120     # 2 minutes
        }.get(persona.technical_level, 300)
        
        if total_time > expected_time:
            time_penalty = (total_time - expected_time) / expected_time
            base_score -= time_penalty
        
        # Success factor
        successful_steps = len([s for s in experience["steps"] if s.get("success", False)])
        total_steps = len(experience["steps"])
        if total_steps > 0:
            success_rate = successful_steps / total_steps
            base_score *= success_rate
        
        # Clamp score between 1 and 10
        return max(1.0, min(10.0, base_score))
    
    def run_user_experience_tests(self, installer_files: List[Path]) -> Dict:
        """Run user experience tests for all personas and installers"""
        logger.info("🎭 Starting user experience simulation tests")
        
        all_experiences = []
        
        for installer_path in installer_files:
            logger.info(f"📦 Testing installer: {installer_path.name}")
            
            for persona_name, persona in self.user_personas.items():
                experience = self.simulate_installation_experience(installer_path, persona)
                all_experiences.append(experience)
                self.test_session["user_tests"].append(experience)
        
        # Calculate summary statistics
        self.calculate_summary_statistics()
        
        # Generate report
        self.generate_ux_report()
        
        return self.test_session
    
    def calculate_summary_statistics(self):
        """Calculate summary statistics from all user tests"""
        tests = self.test_session["user_tests"]
        
        if not tests:
            return
        
        # Count successful installations and first runs
        successful_installations = len([t for t in tests if t.get("success", False)])
        self.test_session["summary"]["successful_installations"] = successful_installations
        
        # Calculate average satisfaction score
        satisfaction_scores = [t.get("satisfaction_score", 0) for t in tests]
        if satisfaction_scores:
            self.test_session["summary"]["user_satisfaction_score"] = sum(satisfaction_scores) / len(satisfaction_scores)
        
        # Calculate average installation time
        installation_times = [t.get("total_time_seconds", 0) for t in tests]
        if installation_times:
            self.test_session["summary"]["average_installation_time"] = sum(installation_times) / len(installation_times)
        
        # Collect common pain points
        all_pain_points = []
        for test in tests:
            all_pain_points.extend(test.get("pain_points", []))
        
        # Count pain point frequency
        pain_point_counts = {}
        for pain_point in all_pain_points:
            pain_point_counts[pain_point] = pain_point_counts.get(pain_point, 0) + 1
        
        # Get top 5 most common pain points
        sorted_pain_points = sorted(pain_point_counts.items(), key=lambda x: x[1], reverse=True)
        self.test_session["summary"]["common_pain_points"] = sorted_pain_points[:5]
    
    def generate_ux_report(self):
        """Generate comprehensive UX test report"""
        self.test_session["end_time"] = datetime.now(timezone.utc).isoformat()
        
        # Save detailed JSON report
        report_file = self.test_results_dir / f"ux_report_{self.test_session['session_id']}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_session, f, indent=2)
        
        # Generate markdown report
        self.generate_ux_markdown_report()
        
        logger.info(f"📊 UX test report saved: {report_file}")
    
    def generate_ux_markdown_report(self):
        """Generate markdown UX test report"""
        session = self.test_session
        summary = session["summary"]
        
        markdown_content = f"""# User Experience Test Report

## Test Session Information
- **Session ID**: {session['session_id']}
- **Platform**: {session['platform']}
- **Start Time**: {session['start_time']}
- **End Time**: {session.get('end_time', 'In Progress')}

## Summary Statistics
- **Total User Personas Tested**: {summary['total_personas']}
- **Successful Installations**: {summary['successful_installations']} / {len(session['user_tests'])}
- **Average User Satisfaction**: {summary['user_satisfaction_score']:.1f} / 10.0
- **Average Installation Time**: {summary['average_installation_time']:.1f} seconds

## User Satisfaction by Persona

| Persona | Technical Level | Avg Satisfaction | Success Rate |
|---------|----------------|------------------|--------------|
"""
        
        # Calculate per-persona statistics
        persona_stats = {}
        for test in session["user_tests"]:
            persona = test["persona"]
            if persona not in persona_stats:
                persona_stats[persona] = {
                    "technical_level": test["technical_level"],
                    "satisfaction_scores": [],
                    "successes": 0,
                    "total": 0
                }
            
            persona_stats[persona]["satisfaction_scores"].append(test.get("satisfaction_score", 0))
            persona_stats[persona]["successes"] += 1 if test.get("success", False) else 0
            persona_stats[persona]["total"] += 1
        
        for persona, stats in persona_stats.items():
            avg_satisfaction = sum(stats["satisfaction_scores"]) / len(stats["satisfaction_scores"]) if stats["satisfaction_scores"] else 0
            success_rate = (stats["successes"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            markdown_content += f"| {persona} | {stats['technical_level']} | {avg_satisfaction:.1f} | {success_rate:.1f}% |\n"
        
        # Common pain points
        markdown_content += f"""
## Most Common Pain Points

"""
        for pain_point, count in summary["common_pain_points"]:
            percentage = (count / len(session["user_tests"]) * 100) if session["user_tests"] else 0
            markdown_content += f"- **{pain_point}**: {count} users ({percentage:.1f}%)\n"
        
        # Recommendations
        markdown_content += f"""
## Recommendations

"""
        
        avg_satisfaction = summary["user_satisfaction_score"]
        if avg_satisfaction >= 8.0:
            markdown_content += "🎉 **Excellent User Experience**: Users are very satisfied with the installation process.\n\n"
        elif avg_satisfaction >= 6.0:
            markdown_content += "✅ **Good User Experience**: Most users are satisfied, but there's room for improvement.\n\n"
        elif avg_satisfaction >= 4.0:
            markdown_content += "⚠️ **Needs Improvement**: User experience has significant issues that should be addressed.\n\n"
        else:
            markdown_content += "❌ **Poor User Experience**: Major UX problems that need immediate attention.\n\n"
        
        # Specific recommendations based on pain points
        if summary["common_pain_points"]:
            markdown_content += "### Specific Improvements Needed:\n\n"
            for pain_point, count in summary["common_pain_points"][:3]:  # Top 3
                if "security warning" in pain_point.lower():
                    markdown_content += "- **Improve security warning documentation**: Provide clearer guidance for handling security warnings\n"
                elif "too long" in pain_point.lower():
                    markdown_content += "- **Optimize performance**: Reduce installation and startup times\n"
                elif "confusion" in pain_point.lower():
                    markdown_content += "- **Simplify user interface**: Make the process more intuitive for non-technical users\n"
                elif "discovery" in pain_point.lower():
                    markdown_content += "- **Improve miner discovery**: Make auto-discovery more reliable and provide better manual options\n"
        
        # Save markdown report
        report_file = self.test_results_dir / f"ux_report_{session['session_id']}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"📄 UX markdown report saved: {report_file}")

def main():
    """Main UX testing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="User experience testing simulator")
    parser.add_argument("--installer-dir", help="Directory containing installer files")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize simulator
    simulator = UserExperienceSimulator(args.project_root)
    
    # Find installer files
    from test_cross_platform_automation import CrossPlatformTester
    tester = CrossPlatformTester(args.project_root)
    
    if args.installer_dir:
        installer_files = tester.find_installer_files(Path(args.installer_dir))
    else:
        installer_files = tester.find_installer_files()
    
    if not installer_files:
        logger.error("❌ No installer files found to test")
        sys.exit(1)
    
    # Run UX tests
    results = simulator.run_user_experience_tests(installer_files)
    
    # Print summary
    summary = results["summary"]
    logger.info(f"🎭 UX Testing Complete:")
    logger.info(f"   Average Satisfaction: {summary['user_satisfaction_score']:.1f}/10.0")
    logger.info(f"   Success Rate: {summary['successful_installations']}/{len(results['user_tests'])}")
    logger.info(f"   Average Time: {summary['average_installation_time']:.1f} seconds")
    
    # Exit with appropriate code based on satisfaction
    success = summary["user_satisfaction_score"] >= 6.0
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()