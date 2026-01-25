from django.test import TestCase
from unittest.mock import patch, MagicMock
from .ai_service import AIContentAnalyzer, ai_analyzer
from .models import Post, Tag

class ModerationTestCase(TestCase):
    def setUp(self):
        self.analyzer = AIContentAnalyzer()

    @patch('core.ai_service.pipeline')
    def test_load_model_success(self, mock_pipeline):
        """Test that model loads successfully"""
        mock_pipeline.return_value = MagicMock()
        self.analyzer.load_model()
        self.assertTrue(self.analyzer._is_loaded)
        mock_pipeline.assert_called_once()

    @patch('core.ai_service.pipeline')
    def test_load_model_failure(self, mock_pipeline):
        """Test graceful failure when model cannot load"""
        mock_pipeline.side_effect = Exception("Download failed")
        self.analyzer.load_model()
        self.assertFalse(self.analyzer._is_loaded)

    def test_fallback_logic_safe(self):
        """Test fallback logic for safe content"""
        # Ensure model is marked as not loaded
        self.analyzer._is_loaded = False
        # Mock load_model to do nothing so it remains unloaded
        self.analyzer.load_model = MagicMock()
        
        result = self.analyzer.analyze_post("I love sunny days")
        self.assertTrue(result['is_safe'])
        self.assertIsNone(result['flag_reason'])
        self.assertEqual(len(result['tags']), 3)

    def test_fallback_logic_unsafe(self):
        """Test fallback logic for unsafe content"""
        self.analyzer._is_loaded = False
        self.analyzer.load_model = MagicMock()
        
        result = self.analyzer.analyze_post("I hate everything")
        self.assertFalse(result['is_safe'])
        self.assertIn("Fallback", result['flag_reason'])

    @patch('core.ai_service.pipeline')
    def test_ai_analysis_safe(self, mock_pipeline):
        """Test full AI analysis flow for safe content"""
        # Setup Mock
        mock_classifier = MagicMock()
        mock_pipeline.return_value = mock_classifier
        
        # Mock responses
        # 1. Safety check
        # Returns dict with 'labels' and 'scores'
        def side_effect(text, labels, multi_label=False):
            if "Safe" in labels: # Safety check
                return {'labels': ['Safe', 'Hate Speech'], 'scores': [0.99, 0.01]}
            else: # Tagging
                return {'labels': ['Happy', 'Hopeful', 'Joy', 'Sad'], 'scores': [0.9, 0.8, 0.7, 0.1]}
        
        mock_classifier.side_effect = side_effect
        
        self.analyzer.load_model()
        result = self.analyzer.analyze_post("This is a wonderful day")
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(len(result['tags']), 3)
        self.assertEqual(result['tags'][0], 'Happy')

    @patch('core.ai_service.pipeline')
    def test_ai_analysis_unsafe(self, mock_pipeline):
        """Test full AI analysis flow for unsafe content"""
        mock_classifier = MagicMock()
        mock_pipeline.return_value = mock_classifier
        
        # Mock unsafe response
        def side_effect(text, labels, multi_label=False):
            if "Safe" in labels: 
                return {'labels': ['Hate Speech', 'Safe'], 'scores': [0.95, 0.05]}
            return {'labels': [], 'scores': []} # Should not reach here if unsafe, but strictly speaking tagging happens after?
            # Wait, code says:
            # if top_label in ["Hate Speech", "Violence"] ... is_safe = False ... 
            # Then it proceeds to tagging anyway.
            
        mock_classifier.side_effect = side_effect
        
        self.analyzer.load_model()
        # Mock tagging call as well
        mock_classifier.return_value = {'labels': ['Dark', 'Angry'], 'scores': [0.9, 0.8]}
        
        # But wait, side_effect overrides return_value. 
        # I need a robust side_effect that handles both calls.
        def robust_side_effect(text, labels, multi_label=False):
            if "Safe" in labels:
                 return {'labels': ['Hate Speech', 'Safe'], 'scores': [0.95, 0.05]}
            else:
                 return {'labels': ['Dark', 'Angry', 'Sad'], 'scores': [0.9, 0.8, 0.7]}

        mock_classifier.side_effect = robust_side_effect

        result = self.analyzer.analyze_post("I hate everyone")
        
    def test_pii_email(self):
        """Test detection of email addresses"""
        result = self.analyzer.analyze_post("Contact me at test@example.com")
        self.assertFalse(result['is_safe'])
        self.assertEqual(result['flag_reason'], "Contains Email Address")

    def test_pii_phone(self):
        """Test detection of phone numbers"""
        result = self.analyzer.analyze_post("Call me at 123-456-7890")
        self.assertFalse(result['is_safe'])
        self.assertEqual(result['flag_reason'], "Contains Phone Number")

    @patch('core.ai_service.pipeline')
    def test_ai_harassment(self, mock_pipeline):
        """Test harassment detection"""
        mock_classifier = MagicMock()
        mock_pipeline.return_value = mock_classifier
        
        # Mock logic to trigger Harassment flag
        def side_effect(text, labels, multi_label=False):
            if "Safe" in labels:
                 # Harassment > 0.9
                 return {'labels': ['Harassment', 'Safe'], 'scores': [0.95, 0.05]}
            else:
                 return {'labels': ['Angry', 'Dark'], 'scores': [0.9, 0.8]}

        mock_classifier.side_effect = side_effect
        
        self.analyzer.load_model()
        result = self.analyzer.analyze_post("I hate this specific person")
        
        self.assertFalse(result['is_safe'])
        self.assertIn("Harassment", result['flag_reason'])

    @patch('core.ai_service.pipeline')
    def test_ai_personal_info(self, mock_pipeline):
        """Test AI-based PII detection (contextual)"""
        mock_classifier = MagicMock()
        mock_pipeline.return_value = mock_classifier
        
        def side_effect(text, labels, multi_label=False):
            if "Safe" in labels:
                 # Personal Info > 0.8
                 return {'labels': ['Personal Information', 'Safe'], 'scores': [0.85, 0.15]}
            else:
                 return {'labels': ['Confession'], 'scores': [0.9]}

        mock_classifier.side_effect = side_effect
        
        self.analyzer.load_model()
        result = self.analyzer.analyze_post("My home address is 123 Main St")
        
        self.assertFalse(result['is_safe'])
        self.assertIn("Personal Info", result['flag_reason'])

    @patch('core.ai_service.pipeline')
    def test_ai_critical_safety_floor(self, mock_pipeline):
        """Test flagging when Safe score is extremely low"""
        mock_classifier = MagicMock()
        mock_pipeline.return_value = mock_classifier
        
        def side_effect(text, labels, multi_label=False):
            if "Safe" in labels:
                 # Safe is very low
                 return {'labels': ['Hate Speech', 'Harassment', 'Safe'], 'scores': [0.55, 0.43, 0.02]}
            else:
                 return {'labels': ['Confused'], 'scores': [0.9]}

        mock_classifier.side_effect = side_effect
        
        self.analyzer.load_model()
        result = self.analyzer.analyze_post("Extremely toxic")
        
        self.assertFalse(result['is_safe'])
        self.assertIn("Extremely Low Safety Score", result['flag_reason'])
