"""
CloudWatch Metrics Service

Emits custom metrics to AWS CloudWatch for monitoring chatbot performance.
Handles metric emission asynchronously to avoid blocking requests.
"""

import boto3
import logging
import os
from typing import Dict, Optional
from datetime import datetime
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logger = logging.getLogger(__name__)

# Thread pool for async metric emission
_metrics_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metrics")


class MetricsService:
    """
    Service for emitting CloudWatch metrics.
    Emits metrics asynchronously to avoid blocking requests.
    """
    
    def __init__(self):
        """Initialize CloudWatch client."""
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
        self.namespace = 'LiteratureBoot/Chatbot'
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Common dimensions for all metrics
        self.common_dimensions = [
            {'Name': 'Environment', 'Value': self.environment},
            {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'}
        ]
    
    def emit_chatbot_response_time(
        self,
        duration_ms: int,
        user_id: str,
        topic_id: str,
        success: bool = True
    ) -> None:
        """
        Emit chatbot response time metric.
        Target: < 5000ms
        
        Args:
            duration_ms: Response duration in milliseconds
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
            success: Whether the response was successful
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'ChatbotResponse'},
            {'Name': 'Status', 'Value': 'Success' if success else 'Failure'}
        ]
        
        self._emit_metric_async(
            metric_name='ChatbotResponseTime',
            value=duration_ms,
            unit='Milliseconds',
            dimensions=dimensions
        )
    
    def emit_chatbot_success(
        self,
        user_id: str,
        topic_id: str
    ) -> None:
        """
        Emit chatbot success metric.
        Target success rate: > 95%
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'ChatbotResponse'}
        ]
        
        self._emit_metric_async(
            metric_name='ChatbotSuccess',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_chatbot_failure(
        self,
        user_id: str,
        topic_id: str,
        error_type: str
    ) -> None:
        """
        Emit chatbot failure metric.
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
            error_type: Type of error (timeout, api_error, etc.)
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'ChatbotResponse'},
            {'Name': 'ErrorType', 'Value': error_type}
        ]
        
        self._emit_metric_async(
            metric_name='ChatbotFailure',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_chatbot_timeout(
        self,
        user_id: str,
        topic_id: str
    ) -> None:
        """
        Emit chatbot timeout metric.
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'ChatbotResponse'}
        ]
        
        self._emit_metric_async(
            metric_name='ChatbotTimeout',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_description_generation_success(
        self,
        user_id: str,
        topic_id: str,
        duration_ms: int
    ) -> None:
        """
        Emit description generation success metric.
        Target success rate: > 95%
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
            duration_ms: Generation duration in milliseconds
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'DescriptionGeneration'}
        ]
        
        self._emit_metric_async(
            metric_name='DescriptionGenerationSuccess',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_description_generation_failure(
        self,
        user_id: str,
        topic_id: str,
        error_type: str
    ) -> None:
        """
        Emit description generation failure metric.
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
            error_type: Type of error
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'DescriptionGeneration'},
            {'Name': 'ErrorType', 'Value': error_type}
        ]
        
        self._emit_metric_async(
            metric_name='DescriptionGenerationFailure',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_conversation_completion(
        self,
        user_id: str,
        topic_id: str
    ) -> None:
        """
        Emit conversation completion metric.
        Tracks how many conversations are successfully completed.
        
        Args:
            user_id: User ID for dimensions
            topic_id: Topic ID for dimensions
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': 'ConversationCompletion'}
        ]
        
        self._emit_metric_async(
            metric_name='ConversationCompletion',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_bedrock_api_error(
        self,
        error_code: str,
        operation: str
    ) -> None:
        """
        Emit AWS Bedrock API error metric.
        Target error rate: < 5%
        
        Args:
            error_code: AWS error code
            operation: Operation that failed (ChatbotResponse or DescriptionGeneration)
        """
        dimensions = self.common_dimensions + [
            {'Name': 'Operation', 'Value': operation},
            {'Name': 'ErrorCode', 'Value': error_code}
        ]
        
        self._emit_metric_async(
            metric_name='BedrockAPIError',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
    
    def _emit_metric_async(
        self,
        metric_name: str,
        value: float,
        unit: str,
        dimensions: list
    ) -> None:
        """
        Emit metric asynchronously to avoid blocking requests.
        Handles CloudWatch API failures gracefully.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Milliseconds, Count, etc.)
            dimensions: Metric dimensions
        """
        # Submit metric emission to thread pool
        _metrics_executor.submit(
            self._emit_metric_sync,
            metric_name,
            value,
            unit,
            dimensions
        )
    
    def _emit_metric_sync(
        self,
        metric_name: str,
        value: float,
        unit: str,
        dimensions: list
    ) -> None:
        """
        Synchronously emit metric to CloudWatch.
        Called by thread pool executor.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: Metric dimensions
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': dimensions
                    }
                ]
            )
        except ClientError as e:
            # Log CloudWatch API failure but don't raise
            # Metrics failures should not impact request processing
            logger.warning(f"Failed to emit CloudWatch metric {metric_name}: {e}")
        except Exception as e:
            # Catch all other exceptions to prevent metrics from breaking requests
            logger.warning(f"Unexpected error emitting metric {metric_name}: {e}")


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """
    Get or create global metrics service instance.
    Lazy initialization to avoid creating client during imports.
    
    Returns:
        MetricsService instance
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
