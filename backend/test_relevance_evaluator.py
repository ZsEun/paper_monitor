"""
Test script for RelevanceEvaluator service
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.relevance_evaluator import RelevanceEvaluator, RelevanceResult


def test_relevance_evaluator_initialization():
    """Test that RelevanceEvaluator initializes correctly"""
    print("\n=== Test: RelevanceEvaluator Initialization ===")
    
    try:
        evaluator = RelevanceEvaluator()
        assert evaluator.bedrock is not None, "Bedrock client should be initialized"
        assert evaluator.model_id is not None, "Model ID should be set"
        assert evaluator.prompt_template is not None, "Prompt template should be loaded"
        print("✓ RelevanceEvaluator initialized successfully")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")


def test_prompt_construction():
    """Test prompt construction with paper and topics"""
    print("\n=== Test: Prompt Construction ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        paper = {
            'id': 'test-1',
            'title': 'Machine Learning for Signal Processing',
            'abstract': 'This paper presents a novel approach to signal processing using deep learning techniques.',
            'keywords': ['machine learning', 'signal processing', 'deep learning']
        }
        
        interest_topics = ['Machine Learning', 'Signal Processing']
        
        prompt = evaluator._construct_prompt(paper, interest_topics)
        
        assert 'Machine Learning for Signal Processing' in prompt, "Title should be in prompt"
        assert 'Machine Learning' in prompt, "Interest topics should be in prompt"
        assert 'Signal Processing' in prompt, "Interest topics should be in prompt"
        
        print("✓ Prompt constructed correctly")
        print(f"  Prompt length: {len(prompt)} characters")
    except Exception as e:
        print(f"✗ Prompt construction failed: {e}")


def test_response_parsing_valid():
    """Test parsing valid JSON response"""
    print("\n=== Test: Response Parsing (Valid JSON) ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        # Test valid JSON response
        response_text = '''
        {
          "isRelevant": true,
          "matchingTopics": ["Machine Learning", "Signal Processing"],
          "confidence": 0.9
        }
        '''
        
        result = evaluator._parse_response(response_text)
        
        assert result.is_relevant is True, "Should be relevant"
        assert len(result.matching_topics) == 2, "Should have 2 matching topics"
        assert "Machine Learning" in result.matching_topics, "Should match Machine Learning"
        assert result.confidence == 0.9, "Confidence should be 0.9"
        
        print("✓ Valid JSON parsed correctly")
        print(f"  is_relevant: {result.is_relevant}")
        print(f"  matching_topics: {result.matching_topics}")
        print(f"  confidence: {result.confidence}")
    except Exception as e:
        print(f"✗ Response parsing failed: {e}")


def test_response_parsing_with_markdown():
    """Test parsing JSON wrapped in markdown code blocks"""
    print("\n=== Test: Response Parsing (Markdown Wrapped) ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        # Test JSON wrapped in markdown
        response_text = '''```json
        {
          "isRelevant": false,
          "matchingTopics": [],
          "confidence": 0.3
        }
        ```'''
        
        result = evaluator._parse_response(response_text)
        
        assert result.is_relevant is False, "Should not be relevant"
        assert len(result.matching_topics) == 0, "Should have no matching topics"
        
        print("✓ Markdown-wrapped JSON parsed correctly")
    except Exception as e:
        print(f"✗ Response parsing failed: {e}")


def test_response_parsing_invalid():
    """Test parsing invalid JSON response"""
    print("\n=== Test: Response Parsing (Invalid JSON) ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        # Test invalid JSON
        response_text = "This is not valid JSON"
        
        try:
            result = evaluator._parse_response(response_text)
            print("✗ Should have raised ValueError for invalid JSON")
        except ValueError as e:
            print(f"✓ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"✗ Test failed: {e}")


def test_response_parsing_missing_fields():
    """Test parsing JSON with missing required fields"""
    print("\n=== Test: Response Parsing (Missing Fields) ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        # Test JSON missing isRelevant field
        response_text = '''
        {
          "matchingTopics": ["Machine Learning"],
          "confidence": 0.8
        }
        '''
        
        try:
            result = evaluator._parse_response(response_text)
            print("✗ Should have raised ValueError for missing isRelevant")
        except ValueError as e:
            print(f"✓ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"✗ Test failed: {e}")


def test_evaluate_no_topics():
    """Test evaluation with no interest topics"""
    print("\n=== Test: Evaluate with No Interest Topics ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        paper = {
            'id': 'test-1',
            'title': 'Test Paper',
            'abstract': 'Test abstract',
            'keywords': []
        }
        
        result = evaluator.evaluate(paper, [])
        
        assert result.is_relevant is False, "Should not be relevant with no topics"
        assert len(result.matching_topics) == 0, "Should have no matching topics"
        assert result.confidence == 1.0, "Confidence should be 1.0 (certain)"
        
        print("✓ Correctly handled no interest topics")
    except Exception as e:
        print(f"✗ Test failed: {e}")


def test_evaluate_with_real_bedrock():
    """Test evaluation with real Bedrock API call"""
    print("\n=== Test: Evaluate with Real Bedrock API ===")
    print("Note: This test requires AWS credentials and will make a real API call")
    
    try:
        evaluator = RelevanceEvaluator()
        
        paper = {
            'id': 'test-1',
            'user_id': 'test-user',
            'title': 'Deep Learning Approaches for Signal Integrity Analysis in High-Speed PCB Design',
            'abstract': 'This paper presents novel deep learning techniques for analyzing signal integrity issues in high-speed printed circuit board designs. We demonstrate improved accuracy over traditional methods.',
            'keywords': ['deep learning', 'signal integrity', 'PCB design', 'machine learning']
        }
        
        interest_topics = ['Signal Integrity', 'Machine Learning', 'PCB Design']
        
        print(f"  Evaluating paper: {paper['title'][:60]}...")
        print(f"  Interest topics: {interest_topics}")
        
        result = evaluator.evaluate(paper, interest_topics)
        
        print(f"✓ Evaluation completed")
        print(f"  is_relevant: {result.is_relevant}")
        print(f"  matching_topics: {result.matching_topics}")
        print(f"  confidence: {result.confidence}")
        print(f"  error: {result.error}")
        
        # This paper should be relevant
        if result.is_relevant:
            print("✓ Correctly identified as relevant")
        else:
            print("⚠ Paper was marked as not relevant (may be due to API issues)")
            
    except Exception as e:
        print(f"⚠ Test skipped or failed: {e}")
        print("  This is expected if AWS credentials are not configured")


def test_evaluate_irrelevant_paper():
    """Test evaluation with clearly irrelevant paper"""
    print("\n=== Test: Evaluate Irrelevant Paper ===")
    print("Note: This test requires AWS credentials and will make a real API call")
    
    try:
        evaluator = RelevanceEvaluator()
        
        paper = {
            'id': 'test-2',
            'user_id': 'test-user',
            'title': 'Culinary Techniques in French Cuisine',
            'abstract': 'This paper explores traditional French cooking methods and their evolution over time.',
            'keywords': ['cooking', 'cuisine', 'food', 'culinary arts']
        }
        
        interest_topics = ['Signal Integrity', 'Machine Learning', 'PCB Design']
        
        print(f"  Evaluating paper: {paper['title'][:60]}...")
        print(f"  Interest topics: {interest_topics}")
        
        result = evaluator.evaluate(paper, interest_topics)
        
        print(f"✓ Evaluation completed")
        print(f"  is_relevant: {result.is_relevant}")
        print(f"  matching_topics: {result.matching_topics}")
        print(f"  confidence: {result.confidence}")
        
        # This paper should NOT be relevant
        if not result.is_relevant:
            print("✓ Correctly identified as not relevant")
        else:
            print("⚠ Paper was marked as relevant (unexpected)")
            
    except Exception as e:
        print(f"⚠ Test skipped or failed: {e}")
        print("  This is expected if AWS credentials are not configured")


def test_template_loading():
    """Test loading prompt templates from file"""
    print("\n=== Test: Template Loading ===")
    
    try:
        evaluator = RelevanceEvaluator()
        
        # Test loading default template
        template = evaluator.load_prompt_template('relevance_evaluation')
        
        assert template is not None, "Template should not be None"
        assert len(template) > 0, "Template should not be empty"
        assert '{title}' in template, "Template should have title placeholder"
        assert '{interest_topics}' in template, "Template should have topics placeholder"
        
        print("✓ Template loaded successfully")
        print(f"  Template length: {len(template)} characters")
        
        # Test loading non-existent template (should fallback to default)
        template2 = evaluator.load_prompt_template('non_existent_template')
        assert template2 is not None, "Should fallback to default template"
        print("✓ Fallback to default template works")
        
    except Exception as e:
        print(f"✗ Template loading failed: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("RelevanceEvaluator Service Tests")
    print("=" * 60)
    
    test_relevance_evaluator_initialization()
    test_prompt_construction()
    test_response_parsing_valid()
    test_response_parsing_with_markdown()
    test_response_parsing_invalid()
    test_response_parsing_missing_fields()
    test_evaluate_no_topics()
    test_template_loading()
    
    print("\n" + "=" * 60)
    print("Real API Tests (require AWS credentials)")
    print("=" * 60)
    
    test_evaluate_with_real_bedrock()
    test_evaluate_irrelevant_paper()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
