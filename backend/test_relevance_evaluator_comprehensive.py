"""
Tests for Relevance_Evaluator with comprehensive descriptions.

Tests Task 11.1 and 11.2: Backward compatibility and comprehensive description usage.
"""
import pytest
from unittest.mock import Mock, patch
from app.services.relevance_evaluator import RelevanceEvaluator, RelevanceResult


@pytest.fixture
def evaluator():
    """Create a RelevanceEvaluator instance"""
    return RelevanceEvaluator()


@pytest.fixture
def sample_paper():
    """Sample paper for testing"""
    return {
        'id': 'paper-123',
        'title': 'Advanced Signal Integrity Analysis in High-Speed PCB Design',
        'abstract': 'This paper presents novel techniques for analyzing signal integrity in high-speed printed circuit boards using electromagnetic simulation and measurement validation.',
        'keywords': ['signal integrity', 'PCB design', 'electromagnetic simulation'],
        'user_id': 'user-456'
    }


def test_evaluate_with_simple_topic_text(evaluator, sample_paper):
    """
    Test backward compatibility: evaluator works with simple topicText.
    
    Task 11.2: Verify evaluator works with simple topicText
    """
    # Mock Bedrock response
    with patch.object(evaluator, '_call_bedrock') as mock_bedrock:
        mock_bedrock.return_value = '''
        {
            "isRelevant": true,
            "matchingTopics": ["Signal Integrity"],
            "confidence": 0.95
        }
        '''
        
        # Pass topics as dictionaries with only topicText (no comprehensiveDescription)
        interest_topics = [
            {'topicText': 'Signal Integrity'},
            {'topicText': 'Power Integrity'}
        ]
        
        result = evaluator.evaluate(sample_paper, interest_topics)
        
        assert result.is_relevant is True
        assert 'Signal Integrity' in result.matching_topics
        assert result.confidence == 0.95
        assert result.error is None
        
        # Verify the prompt was constructed with topicText
        call_args = mock_bedrock.call_args[0][0]
        assert 'Signal Integrity' in call_args
        assert 'Power Integrity' in call_args


def test_evaluate_with_comprehensive_description(evaluator, sample_paper):
    """
    Test that evaluator uses comprehensiveDescription when available.
    
    Task 11.1: Verify evaluator uses comprehensiveDescription
    """
    # Mock Bedrock response
    with patch.object(evaluator, '_call_bedrock') as mock_bedrock:
        mock_bedrock.return_value = '''
        {
            "isRelevant": true,
            "matchingTopics": ["Signal Integrity"],
            "confidence": 0.98
        }
        '''
        
        # Pass topics with comprehensive descriptions
        interest_topics = [
            {
                'topicText': 'Signal Integrity',
                'comprehensiveDescription': 'Research focused on signal integrity in high-speed digital systems, including transmission line analysis, impedance matching, crosstalk mitigation, and electromagnetic simulation techniques. Particularly interested in PCB design methodologies and measurement validation approaches.'
            },
            {
                'topicText': 'Power Integrity',
                'comprehensiveDescription': 'Power distribution network design and analysis, including decoupling strategies, PDN impedance optimization, and voltage regulation.'
            }
        ]
        
        result = evaluator.evaluate(sample_paper, interest_topics)
        
        assert result.is_relevant is True
        assert result.error is None
        
        # Verify the prompt was constructed with comprehensiveDescription (not just topicText)
        call_args = mock_bedrock.call_args[0][0]
        assert 'transmission line analysis' in call_args
        assert 'impedance matching' in call_args
        assert 'crosstalk mitigation' in call_args
        # Should NOT contain just the simple topicText
        assert call_args.count('Signal Integrity') < 3  # Appears in description but not as standalone


def test_evaluate_fallback_to_topic_text(evaluator, sample_paper):
    """
    Test that evaluator falls back to topicText when comprehensiveDescription is empty.
    
    Task 11.2: Verify backward compatibility with missing/empty descriptions
    """
    # Mock Bedrock response
    with patch.object(evaluator, '_call_bedrock') as mock_bedrock:
        mock_bedrock.return_value = '''
        {
            "isRelevant": true,
            "matchingTopics": ["Signal Integrity"],
            "confidence": 0.90
        }
        '''
        
        # Pass topics with empty or None comprehensiveDescription
        interest_topics = [
            {
                'topicText': 'Signal Integrity',
                'comprehensiveDescription': None  # Should fall back to topicText
            },
            {
                'topicText': 'Power Integrity',
                'comprehensiveDescription': ''  # Empty string - should fall back to topicText
            },
            {
                'topicText': 'EMC',
                'comprehensiveDescription': '   '  # Whitespace only - should fall back to topicText
            }
        ]
        
        result = evaluator.evaluate(sample_paper, interest_topics)
        
        assert result.is_relevant is True
        assert result.error is None
        
        # Verify the prompt was constructed with topicText (fallback)
        call_args = mock_bedrock.call_args[0][0]
        assert 'Signal Integrity' in call_args
        assert 'Power Integrity' in call_args
        assert 'EMC' in call_args


def test_evaluate_mixed_topics(evaluator, sample_paper):
    """
    Test evaluator with mixed topics (some with descriptions, some without).
    
    Task 11.2: Verify backward compatibility with mixed topic types
    """
    # Mock Bedrock response
    with patch.object(evaluator, '_call_bedrock') as mock_bedrock:
        mock_bedrock.return_value = '''
        {
            "isRelevant": true,
            "matchingTopics": ["Signal Integrity"],
            "confidence": 0.92
        }
        '''
        
        # Mix of topics with and without comprehensive descriptions
        interest_topics = [
            {
                'topicText': 'Signal Integrity',
                'comprehensiveDescription': 'Detailed description of signal integrity research interests including transmission lines and crosstalk.'
            },
            {
                'topicText': 'Power Integrity'
                # No comprehensiveDescription field at all
            },
            {
                'topicText': 'EMC',
                'comprehensiveDescription': None
            }
        ]
        
        result = evaluator.evaluate(sample_paper, interest_topics)
        
        assert result.is_relevant is True
        assert result.error is None
        
        # Verify prompt contains both comprehensive description and simple topicText
        call_args = mock_bedrock.call_args[0][0]
        assert 'transmission lines' in call_args  # From comprehensive description
        assert 'Power Integrity' in call_args  # Simple topicText
        assert 'EMC' in call_args  # Fallback to topicText


def test_evaluate_legacy_string_topics(evaluator, sample_paper):
    """
    Test backward compatibility with legacy string-based topics.
    
    Task 11.2: Verify evaluator still works with old string format
    """
    # Mock Bedrock response
    with patch.object(evaluator, '_call_bedrock') as mock_bedrock:
        mock_bedrock.return_value = '''
        {
            "isRelevant": true,
            "matchingTopics": ["Signal Integrity"],
            "confidence": 0.88
        }
        '''
        
        # Pass topics as strings (legacy format)
        interest_topics = ['Signal Integrity', 'Power Integrity']
        
        result = evaluator.evaluate(sample_paper, interest_topics)
        
        assert result.is_relevant is True
        assert result.error is None
        
        # Verify prompt was constructed
        call_args = mock_bedrock.call_args[0][0]
        assert 'Signal Integrity' in call_args
        assert 'Power Integrity' in call_args
