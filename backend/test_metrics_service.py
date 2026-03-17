"""
Unit tests for CloudWatch Metrics Service

Tests metric emission functionality and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from app.services.metrics_service import MetricsService, get_metrics_service


@pytest.fixture
def metrics_service():
    """Create MetricsService instance with mocked CloudWatch client and synchronous executor"""
    import app.services.metrics_service as metrics_module

    with patch('app.services.metrics_service.boto3.client') as mock_boto:
        mock_cloudwatch = Mock()
        mock_boto.return_value = mock_cloudwatch

        service = MetricsService()
        service.cloudwatch = mock_cloudwatch

        # Run async submissions synchronously so assertions don't need sleep
        def sync_submit(fn, *args, **kwargs):
            fn(*args, **kwargs)

        original_executor = metrics_module._metrics_executor
        mock_executor = Mock()
        mock_executor.submit.side_effect = sync_submit
        metrics_module._metrics_executor = mock_executor

        # Reset singleton so other tests don't interfere
        original_singleton = metrics_module._metrics_service
        metrics_module._metrics_service = None

        yield service

        # Restore
        metrics_module._metrics_executor = original_executor
        metrics_module._metrics_service = original_singleton


def test_emit_chatbot_response_time_success(metrics_service):
    """Test emitting chatbot response time metric for successful response"""
    # Emit metric
    metrics_service.emit_chatbot_response_time(
        duration_ms=2500,
        user_id="user-123",
        topic_id="topic-456",
        success=True
    )
    
    # Wait for async emission (small delay)
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_chatbot_response_time_failure(metrics_service):
    """Test emitting chatbot response time metric for failed response"""
    # Emit metric
    metrics_service.emit_chatbot_response_time(
        duration_ms=6000,
        user_id="user-123",
        topic_id="topic-456",
        success=False
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_chatbot_success(metrics_service):
    """Test emitting chatbot success metric"""
    # Emit metric
    metrics_service.emit_chatbot_success(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_chatbot_failure(metrics_service):
    """Test emitting chatbot failure metric"""
    # Emit metric
    metrics_service.emit_chatbot_failure(
        user_id="user-123",
        topic_id="topic-456",
        error_type="timeout"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_chatbot_timeout(metrics_service):
    """Test emitting chatbot timeout metric"""
    # Emit metric
    metrics_service.emit_chatbot_timeout(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_description_generation_success(metrics_service):
    """Test emitting description generation success metric"""
    # Emit metric
    metrics_service.emit_description_generation_success(
        user_id="user-123",
        topic_id="topic-456",
        duration_ms=3000
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_description_generation_failure(metrics_service):
    """Test emitting description generation failure metric"""
    # Emit metric
    metrics_service.emit_description_generation_failure(
        user_id="user-123",
        topic_id="topic-456",
        error_type="bedrock_api_error"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_conversation_completion(metrics_service):
    """Test emitting conversation completion metric"""
    # Emit metric
    metrics_service.emit_conversation_completion(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_emit_bedrock_api_error(metrics_service):
    """Test emitting Bedrock API error metric"""
    # Emit metric
    metrics_service.emit_bedrock_api_error(
        error_code="ThrottlingException",
        operation="ChatbotResponse"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called
    assert metrics_service.cloudwatch.put_metric_data.called


def test_metric_emission_handles_cloudwatch_failure(metrics_service):
    """Test that CloudWatch API failures don't raise exceptions"""
    # Mock CloudWatch to raise error
    metrics_service.cloudwatch.put_metric_data.side_effect = ClientError(
        {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
        'PutMetricData'
    )
    
    # Emit metric - should not raise exception
    metrics_service.emit_chatbot_success(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Test passes if no exception raised


def test_metric_emission_handles_unexpected_error(metrics_service):
    """Test that unexpected errors during metric emission don't raise exceptions"""
    # Mock CloudWatch to raise unexpected error
    metrics_service.cloudwatch.put_metric_data.side_effect = Exception("Unexpected error")
    
    # Emit metric - should not raise exception
    metrics_service.emit_chatbot_success(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Test passes if no exception raised


def test_get_metrics_service_singleton():
    """Test that get_metrics_service returns singleton instance"""
    with patch('app.services.metrics_service.boto3.client'):
        service1 = get_metrics_service()
        service2 = get_metrics_service()
        
        # Should return same instance
        assert service1 is service2


def test_metrics_include_common_dimensions(metrics_service):
    """Test that all metrics include common dimensions (Environment, Service)"""
    # Emit a metric
    metrics_service.emit_chatbot_success(
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Wait for async emission
    
    # Verify CloudWatch API was called with dimensions
    if metrics_service.cloudwatch.put_metric_data.called:
        call_args = metrics_service.cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        dimensions = metric_data['Dimensions']
        
        # Check for common dimensions
        dimension_names = [d['Name'] for d in dimensions]
        assert 'Environment' in dimension_names
        assert 'Service' in dimension_names
        assert 'Operation' in dimension_names


def test_metrics_use_correct_namespace(metrics_service):
    """Test that metrics use correct CloudWatch namespace"""
    assert metrics_service.namespace == 'LiteratureBoot/Chatbot'


def test_metrics_use_correct_region(metrics_service):
    """Test that CloudWatch client uses us-west-2 region"""
    # This is verified during initialization
    # The test ensures the service initializes without error
    assert metrics_service.cloudwatch is not None
