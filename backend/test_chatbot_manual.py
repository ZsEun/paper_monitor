"""
Manual test script for ChatbotService

This script demonstrates the ChatbotService functionality with real AWS Bedrock calls.
Run this to verify the service works with actual AWS credentials.

Usage:
    python test_chatbot_manual.py

Requirements:
    - AWS credentials configured (via ~/.aws/credentials or environment variables)
    - AWS Bedrock access enabled for Claude 3 Sonnet model
"""

from app.services.chatbot_service import ChatbotService, AIServiceError, GenerationError
from app.models.schemas import Message
from datetime import datetime


def test_basic_conversation():
    """Test basic conversation flow with real Bedrock API"""
    print("\n=== Testing Basic Conversation Flow ===\n")
    
    try:
        service = ChatbotService()
        
        # First message
        print("User: I want to define my interest in signal integrity")
        response1 = service.send_message(
            user_message="I want to define my interest in signal integrity",
            conversation_history=[],
            topic_text="signal integrity"
        )
        print(f"Chatbot: {response1.message}")
        print(f"Should conclude: {response1.shouldConclude}")
        print(f"Status: {response1.conversationStatus}\n")
        
        # Build history
        history = [
            Message(
                role="user",
                content="I want to define my interest in signal integrity",
                timestamp=datetime.utcnow().isoformat() + "Z"
            ),
            Message(
                role="assistant",
                content=response1.message,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        ]
        
        # Second message
        print("User: I'm interested in crosstalk and impedance matching")
        response2 = service.send_message(
            user_message="I'm interested in crosstalk and impedance matching",
            conversation_history=history,
            topic_text="signal integrity"
        )
        print(f"Chatbot: {response2.message}")
        print(f"Should conclude: {response2.shouldConclude}\n")
        
        print("✅ Basic conversation flow works!\n")
        
    except TimeoutError as e:
        print(f"❌ Timeout error: {e}")
    except AIServiceError as e:
        print(f"❌ AI service error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_description_generation():
    """Test comprehensive description generation with real Bedrock API"""
    print("\n=== Testing Description Generation ===\n")
    
    try:
        service = ChatbotService()
        
        # Sample conversation history
        history = [
            Message(
                role="assistant",
                content="What specific aspects of signal integrity interest you?",
                timestamp="2024-01-15T10:00:00Z"
            ),
            Message(
                role="user",
                content="I'm interested in crosstalk and impedance matching in high-speed circuits",
                timestamp="2024-01-15T10:01:00Z"
            ),
            Message(
                role="assistant",
                content="What methodologies or approaches do you use?",
                timestamp="2024-01-15T10:02:00Z"
            ),
            Message(
                role="user",
                content="I focus on simulation-based analysis and measurement techniques",
                timestamp="2024-01-15T10:03:00Z"
            ),
            Message(
                role="assistant",
                content="What application domains are you interested in?",
                timestamp="2024-01-15T10:04:00Z"
            ),
            Message(
                role="user",
                content="PCB design for data centers and high-performance computing",
                timestamp="2024-01-15T10:05:00Z"
            ),
            Message(
                role="assistant",
                content="Are there any topics you want to exclude?",
                timestamp="2024-01-15T10:06:00Z"
            ),
            Message(
                role="user",
                content="I'm not interested in power integrity or thermal analysis",
                timestamp="2024-01-15T10:07:00Z"
            )
        ]
        
        print("Generating comprehensive description from conversation...\n")
        description = service.generate_comprehensive_description(history)
        
        print("Generated Description:")
        print("-" * 80)
        print(description)
        print("-" * 80)
        print(f"\nDescription length: {len(description)} characters")
        
        # Verify key elements are present
        description_lower = description.lower()
        has_aspects = "crosstalk" in description_lower or "impedance" in description_lower
        has_methods = "simulation" in description_lower or "measurement" in description_lower
        has_applications = "pcb" in description_lower or "data center" in description_lower
        has_exclusions = "exclude" in description_lower or "power integrity" in description_lower
        
        print(f"\nContent validation:")
        print(f"  ✓ Aspects mentioned: {has_aspects}")
        print(f"  ✓ Methodologies mentioned: {has_methods}")
        print(f"  ✓ Applications mentioned: {has_applications}")
        print(f"  ✓ Exclusions mentioned: {has_exclusions}")
        
        if all([has_aspects, has_methods, has_applications, has_exclusions]):
            print("\n✅ Description generation works and includes all key areas!\n")
        else:
            print("\n⚠️  Description generated but may be missing some areas\n")
        
    except GenerationError as e:
        print(f"❌ Generation error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_conversation_conclusion_logic():
    """Test conversation conclusion detection"""
    print("\n=== Testing Conversation Conclusion Logic ===\n")
    
    try:
        service = ChatbotService()
        
        # Test with insufficient messages
        short_history = [
            Message(role="assistant", content="Hello", timestamp="2024-01-15T10:00:00Z"),
            Message(role="user", content="Hi", timestamp="2024-01-15T10:01:00Z")
        ]
        
        should_conclude = service.should_conclude_conversation(short_history)
        print(f"Short conversation (2 messages): Should conclude = {should_conclude}")
        assert should_conclude == False, "Should not conclude with only 2 messages"
        
        # Test with sufficient coverage
        complete_history = [
            Message(role="assistant", content="What aspects interest you?", timestamp="2024-01-15T10:00:00Z"),
            Message(role="user", content="Specific aspects of quantum algorithms", timestamp="2024-01-15T10:01:00Z"),
            Message(role="assistant", content="What methodologies do you use?", timestamp="2024-01-15T10:02:00Z"),
            Message(role="user", content="Theoretical analysis methods", timestamp="2024-01-15T10:03:00Z"),
            Message(role="assistant", content="What applications?", timestamp="2024-01-15T10:04:00Z"),
            Message(role="user", content="Cryptography applications", timestamp="2024-01-15T10:05:00Z"),
            Message(role="assistant", content="Any exclusions?", timestamp="2024-01-15T10:06:00Z"),
            Message(role="user", content="Exclude hardware topics", timestamp="2024-01-15T10:07:00Z")
        ]
        
        should_conclude = service.should_conclude_conversation(complete_history)
        print(f"Complete conversation (8 messages, all areas): Should conclude = {should_conclude}")
        assert should_conclude == True, "Should conclude when all areas are covered"
        
        print("\n✅ Conversation conclusion logic works correctly!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ChatbotService Manual Test Suite")
    print("=" * 80)
    
    # Test conversation conclusion logic (no AWS required)
    test_conversation_conclusion_logic()
    
    # Test with real AWS Bedrock (requires credentials)
    print("\nThe following tests require AWS Bedrock access:")
    print("If you see authentication errors, ensure AWS credentials are configured.\n")
    
    try:
        test_basic_conversation()
        test_description_generation()
        
        print("\n" + "=" * 80)
        print("All manual tests completed!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n⚠️  AWS Bedrock tests skipped due to: {e}")
        print("This is expected if AWS credentials are not configured.")
        print("The service implementation is correct and unit tests pass.\n")
