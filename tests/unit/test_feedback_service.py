"""
Unit tests for the FeedbackService.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

from src.backend.services.feedback_service import FeedbackService


class TestFeedbackService(unittest.TestCase):
    """Test cases for FeedbackService"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.feedback_service = FeedbackService(feedback_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_submit_feedback_success(self):
        """Test successful feedback submission"""
        feedback_data = {
            'category': 'installation',
            'message': 'Test feedback message for installation issues',
            'user_id': 'test_user_123',
            'installer_version': '0.1.0',
            'system_info': {'os': 'Windows 10', 'arch': 'x64'},
            'severity': 'medium'
        }
        
        result = self.feedback_service.submit_feedback(feedback_data)
        
        self.assertTrue(result['success'])
        self.assertIn('feedback_id', result)
        self.assertIn('message', result)
    
    def test_submit_feedback_missing_required_field(self):
        """Test feedback submission with missing required field"""
        feedback_data = {
            'category': 'installation',
            'message': 'Test feedback message',
            # Missing user_id
        }
        
        result = self.feedback_service.submit_feedback(feedback_data)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('user_id', result['error'])
    
    def test_get_feedback_summary_empty(self):
        """Test getting feedback summary when no feedback exists"""
        summary = self.feedback_service.get_feedback_summary()
        
        self.assertEqual(summary['total_feedback'], 0)
        self.assertEqual(len(summary['recent_feedback']), 0)
    
    def test_get_feedback_summary_with_data(self):
        """Test getting feedback summary with existing feedback"""
        # Submit test feedback
        feedback_data = {
            'category': 'bugs',
            'message': 'Test bug report',
            'user_id': 'test_user',
            'severity': 'high'
        }
        
        self.feedback_service.submit_feedback(feedback_data)
        
        summary = self.feedback_service.get_feedback_summary()
        
        self.assertEqual(summary['total_feedback'], 1)
        self.assertEqual(summary['categories']['bugs'], 1)
        self.assertEqual(summary['severity_distribution']['high'], 1)
        self.assertEqual(len(summary['recent_feedback']), 1)
    
    def test_get_feedback_by_category(self):
        """Test getting feedback by category"""
        # Submit feedback in different categories
        feedback1 = {
            'category': 'installation',
            'message': 'Installation issue',
            'user_id': 'user1'
        }
        feedback2 = {
            'category': 'bugs',
            'message': 'Bug report',
            'user_id': 'user2'
        }
        
        self.feedback_service.submit_feedback(feedback1)
        self.feedback_service.submit_feedback(feedback2)
        
        installation_feedback = self.feedback_service.get_feedback_by_category('installation')
        bugs_feedback = self.feedback_service.get_feedback_by_category('bugs')
        
        self.assertEqual(len(installation_feedback), 1)
        self.assertEqual(len(bugs_feedback), 1)
        self.assertEqual(installation_feedback[0]['category'], 'installation')
        self.assertEqual(bugs_feedback[0]['category'], 'bugs')
    
    def test_update_feedback_status(self):
        """Test updating feedback status"""
        # Submit feedback first
        feedback_data = {
            'category': 'installation',
            'message': 'Test feedback',
            'user_id': 'test_user'
        }
        
        result = self.feedback_service.submit_feedback(feedback_data)
        feedback_id = result['feedback_id']
        
        # Update status
        update_result = self.feedback_service.update_feedback_status(
            feedback_id, 'reviewed', 'Reviewed by admin'
        )
        
        self.assertTrue(update_result['success'])
        
        # Verify status was updated
        feedback_file = Path(self.temp_dir) / f"{feedback_id}.json"
        with open(feedback_file, 'r') as f:
            feedback = json.load(f)
        
        self.assertEqual(feedback['status'], 'reviewed')
        self.assertIn('status_history', feedback)
        self.assertEqual(len(feedback['status_history']), 1)
    
    def test_export_feedback_report(self):
        """Test exporting feedback report"""
        # Submit test feedback
        feedback_data = {
            'category': 'installation',
            'message': 'Test feedback for export',
            'user_id': 'test_user'
        }
        
        self.feedback_service.submit_feedback(feedback_data)
        
        # Export report
        output_file = Path(self.temp_dir) / "feedback_report.json"
        result = self.feedback_service.export_feedback_report(str(output_file))
        
        self.assertTrue(result['success'])
        self.assertTrue(output_file.exists())
        
        # Verify report content
        with open(output_file, 'r') as f:
            report = json.load(f)
        
        self.assertIn('generated_at', report)
        self.assertEqual(report['total_feedback_items'], 1)
        self.assertIn('summary', report)
        self.assertIn('feedback_items', report)


if __name__ == '__main__':
    unittest.main()