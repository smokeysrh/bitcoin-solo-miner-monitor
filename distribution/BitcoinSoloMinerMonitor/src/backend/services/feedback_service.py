"""
Community Feedback Service

This service handles community feedback collection, validation, and storage
for the installer distribution system.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service for handling community feedback and validation reports"""
    
    def __init__(self, feedback_dir: str = "community-feedback"):
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        # Initialize feedback categories
        self.categories = {
            'installation': 'Installation Process',
            'verification': 'Verification Process', 
            'security': 'Security Concerns',
            'usability': 'User Experience',
            'bugs': 'Bug Reports',
            'suggestions': 'Feature Suggestions'
        }
        
    def submit_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit community feedback
        
        Args:
            feedback_data: Dictionary containing feedback information
            
        Returns:
            Dictionary with submission result and feedback ID
        """
        try:
            # Validate required fields
            required_fields = ['category', 'message', 'user_id']
            for field in required_fields:
                if field not in feedback_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Generate feedback ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            feedback_id = f"feedback_{timestamp}_{feedback_data.get('user_id', 'anonymous')}"
            
            # Prepare feedback record
            feedback_record = {
                'id': feedback_id,
                'timestamp': datetime.now().isoformat(),
                'category': feedback_data['category'],
                'message': feedback_data['message'],
                'user_id': feedback_data['user_id'],
                'installer_version': feedback_data.get('installer_version', 'unknown'),
                'system_info': feedback_data.get('system_info', {}),
                'severity': feedback_data.get('severity', 'medium'),
                'status': 'submitted'
            }
            
            # Save feedback to file
            feedback_file = self.feedback_dir / f"{feedback_id}.json"
            with open(feedback_file, 'w') as f:
                json.dump(feedback_record, f, indent=2)
            
            logger.info(f"Feedback submitted successfully: {feedback_id}")
            
            return {
                'success': True,
                'feedback_id': feedback_id,
                'message': 'Feedback submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to submit feedback: {str(e)}'
            }
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Get summary of all community feedback
        
        Returns:
            Dictionary containing feedback statistics and summaries
        """
        try:
            feedback_files = list(self.feedback_dir.glob("feedback_*.json"))
            
            if not feedback_files:
                return {
                    'total_feedback': 0,
                    'categories': {},
                    'recent_feedback': []
                }
            
            # Initialize counters
            category_counts = {cat: 0 for cat in self.categories.keys()}
            severity_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            recent_feedback = []
            
            # Process each feedback file
            for feedback_file in feedback_files:
                try:
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                    
                    # Count by category
                    category = feedback.get('category', 'unknown')
                    if category in category_counts:
                        category_counts[category] += 1
                    
                    # Count by severity
                    severity = feedback.get('severity', 'medium')
                    if severity in severity_counts:
                        severity_counts[severity] += 1
                    
                    # Add to recent feedback (last 10)
                    recent_feedback.append({
                        'id': feedback.get('id'),
                        'timestamp': feedback.get('timestamp'),
                        'category': feedback.get('category'),
                        'severity': feedback.get('severity'),
                        'message_preview': feedback.get('message', '')[:100] + '...' if len(feedback.get('message', '')) > 100 else feedback.get('message', '')
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing feedback file {feedback_file}: {str(e)}")
                    continue
            
            # Sort recent feedback by timestamp (newest first)
            recent_feedback.sort(key=lambda x: x['timestamp'], reverse=True)
            recent_feedback = recent_feedback[:10]
            
            return {
                'total_feedback': len(feedback_files),
                'categories': category_counts,
                'severity_distribution': severity_counts,
                'recent_feedback': recent_feedback
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback summary: {str(e)}")
            return {
                'total_feedback': 0,
                'categories': {},
                'error': str(e)
            }
    
    def get_feedback_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific category
        
        Args:
            category: Feedback category to filter by
            
        Returns:
            List of feedback records for the specified category
        """
        try:
            if category not in self.categories:
                return []
            
            feedback_files = list(self.feedback_dir.glob("feedback_*.json"))
            category_feedback = []
            
            for feedback_file in feedback_files:
                try:
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                    
                    if feedback.get('category') == category:
                        category_feedback.append(feedback)
                        
                except Exception as e:
                    logger.warning(f"Error processing feedback file {feedback_file}: {str(e)}")
                    continue
            
            # Sort by timestamp (newest first)
            category_feedback.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return category_feedback
            
        except Exception as e:
            logger.error(f"Error getting feedback by category: {str(e)}")
            return []
    
    def update_feedback_status(self, feedback_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """
        Update the status of a feedback item
        
        Args:
            feedback_id: ID of the feedback to update
            status: New status (submitted, reviewed, in_progress, resolved, closed)
            notes: Optional notes about the status change
            
        Returns:
            Dictionary with update result
        """
        try:
            feedback_file = self.feedback_dir / f"{feedback_id}.json"
            
            if not feedback_file.exists():
                return {
                    'success': False,
                    'error': f'Feedback {feedback_id} not found'
                }
            
            # Load existing feedback
            with open(feedback_file, 'r') as f:
                feedback = json.load(f)
            
            # Update status and add status history
            old_status = feedback.get('status', 'unknown')
            feedback['status'] = status
            feedback['last_updated'] = datetime.now().isoformat()
            
            # Initialize status history if it doesn't exist
            if 'status_history' not in feedback:
                feedback['status_history'] = []
            
            # Add status change to history
            feedback['status_history'].append({
                'timestamp': datetime.now().isoformat(),
                'old_status': old_status,
                'new_status': status,
                'notes': notes
            })
            
            # Save updated feedback
            with open(feedback_file, 'w') as f:
                json.dump(feedback, f, indent=2)
            
            logger.info(f"Feedback {feedback_id} status updated from {old_status} to {status}")
            
            return {
                'success': True,
                'message': f'Feedback status updated to {status}'
            }
            
        except Exception as e:
            logger.error(f"Error updating feedback status: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to update feedback status: {str(e)}'
            }
    
    def export_feedback_report(self, output_file: str = None) -> Dict[str, Any]:
        """
        Export all feedback to a comprehensive report
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Dictionary with export result and report data
        """
        try:
            feedback_files = list(self.feedback_dir.glob("feedback_*.json"))
            all_feedback = []
            
            # Collect all feedback
            for feedback_file in feedback_files:
                try:
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                    all_feedback.append(feedback)
                except Exception as e:
                    logger.warning(f"Error processing feedback file {feedback_file}: {str(e)}")
                    continue
            
            # Generate report
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_feedback_items': len(all_feedback),
                'summary': self.get_feedback_summary(),
                'feedback_items': all_feedback
            }
            
            # Save to file if specified
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
                
                logger.info(f"Feedback report exported to {output_file}")
            
            return {
                'success': True,
                'report': report,
                'output_file': output_file
            }
            
        except Exception as e:
            logger.error(f"Error exporting feedback report: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to export feedback report: {str(e)}'
            }