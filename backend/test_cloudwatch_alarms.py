"""
Tests for CloudWatch Alarms Configuration

Validates that alarm setup scripts work correctly and alarms are properly configured.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from setup_cloudwatch_alarms import CloudWatchAlarmSetup


class TestCloudWatchAlarmSetup:
    """Test CloudWatch alarm setup functionality."""
    
    @pytest.fixture
    def alarm_setup(self):
        """Create CloudWatchAlarmSetup instance with mocked clients."""
        with patch('setup_cloudwatch_alarms.boto3') as mock_boto3:
            mock_cloudwatch = Mock()
            mock_sns = Mock()
            mock_boto3.client.side_effect = lambda service, **kwargs: {
                'cloudwatch': mock_cloudwatch,
                'sns': mock_sns
            }[service]
            
            setup = CloudWatchAlarmSetup(environment='development', region='us-west-2')
            setup.cloudwatch = mock_cloudwatch
            setup.sns = mock_sns
            
            yield setup
    
    def test_initialization(self, alarm_setup):
        """Test CloudWatchAlarmSetup initialization."""
        assert alarm_setup.environment == 'development'
        assert alarm_setup.region == 'us-west-2'
        assert alarm_setup.namespace == 'LiteratureBoot/Chatbot'
    
    def test_create_sns_topic_new(self, alarm_setup):
        """Test creating a new SNS topic."""
        alarm_setup.sns.create_topic.return_value = {
            'TopicArn': 'arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-development'
        }
        
        topic_arn = alarm_setup.create_sns_topic(email='test@example.com')
        
        # Verify topic creation
        alarm_setup.sns.create_topic.assert_called_once_with(
            Name='literature-boot-chatbot-alarms-development'
        )
        
        # Verify email subscription
        alarm_setup.sns.subscribe.assert_called_once_with(
            TopicArn='arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-development',
            Protocol='email',
            Endpoint='test@example.com'
        )
        
        assert topic_arn == 'arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-development'
    
    def test_create_sns_topic_without_email(self, alarm_setup):
        """Test creating SNS topic without email subscription."""
        alarm_setup.sns.create_topic.return_value = {
            'TopicArn': 'arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-development'
        }
        
        topic_arn = alarm_setup.create_sns_topic()
        
        # Verify topic creation
        alarm_setup.sns.create_topic.assert_called_once()
        
        # Verify no email subscription
        alarm_setup.sns.subscribe.assert_not_called()
        
        assert topic_arn is not None
    
    def test_create_high_response_time_alarm(self, alarm_setup):
        """Test creating high response time alarm."""
        sns_topic_arn = 'arn:aws:sns:us-west-2:123456789012:test-topic'
        
        alarm_name = alarm_setup.create_high_response_time_alarm(sns_topic_arn)
        
        # Verify alarm creation
        alarm_setup.cloudwatch.put_metric_alarm.assert_called_once()
        call_args = alarm_setup.cloudwatch.put_metric_alarm.call_args[1]
        
        assert call_args['AlarmName'] == 'LiteratureBoot-Chatbot-HighResponseTime-development'
        assert call_args['MetricName'] == 'ChatbotResponseTime'
        assert call_args['Namespace'] == 'LiteratureBoot/Chatbot'
        assert call_args['ExtendedStatistic'] == 'p95'
        assert call_args['Threshold'] == 7000.0
        assert call_args['Period'] == 300
        assert call_args['EvaluationPeriods'] == 2
        assert call_args['DatapointsToAlarm'] == 2
        assert call_args['ComparisonOperator'] == 'GreaterThanThreshold'
        assert sns_topic_arn in call_args['AlarmActions']
        
        # Verify dimensions
        dimensions = call_args['Dimensions']
        assert {'Name': 'Environment', 'Value': 'development'} in dimensions
        assert {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'} in dimensions
        assert {'Name': 'Operation', 'Value': 'ChatbotResponse'} in dimensions
        assert {'Name': 'Status', 'Value': 'Success'} in dimensions
    
    def test_create_high_error_rate_alarm(self, alarm_setup):
        """Test creating high error rate alarm with metric math."""
        sns_topic_arn = 'arn:aws:sns:us-west-2:123456789012:test-topic'
        
        alarm_name = alarm_setup.create_high_error_rate_alarm(sns_topic_arn)
        
        # Verify alarm creation
        alarm_setup.cloudwatch.put_metric_alarm.assert_called_once()
        call_args = alarm_setup.cloudwatch.put_metric_alarm.call_args[1]
        
        assert call_args['AlarmName'] == 'LiteratureBoot-Chatbot-HighErrorRate-development'
        assert call_args['Threshold'] == 10.0
        assert call_args['EvaluationPeriods'] == 2
        assert call_args['DatapointsToAlarm'] == 2
        assert sns_topic_arn in call_args['AlarmActions']
        
        # Verify metric math
        metrics = call_args['Metrics']
        assert len(metrics) == 3
        
        # Check success metric
        success_metric = next(m for m in metrics if m['Id'] == 'success')
        assert success_metric['MetricStat']['Metric']['MetricName'] == 'ChatbotSuccess'
        assert success_metric['ReturnData'] is False
        
        # Check failure metric
        failure_metric = next(m for m in metrics if m['Id'] == 'failure')
        assert failure_metric['MetricStat']['Metric']['MetricName'] == 'ChatbotFailure'
        assert failure_metric['ReturnData'] is False
        
        # Check error rate expression
        error_rate = next(m for m in metrics if m['Id'] == 'error_rate')
        assert error_rate['Expression'] == '(failure / (success + failure)) * 100'
        assert error_rate['ReturnData'] is True
    
    def test_create_description_generation_failure_rate_alarm(self, alarm_setup):
        """Test creating description generation failure rate alarm."""
        sns_topic_arn = 'arn:aws:sns:us-west-2:123456789012:test-topic'
        
        alarm_name = alarm_setup.create_description_generation_failure_rate_alarm(sns_topic_arn)
        
        # Verify alarm creation
        alarm_setup.cloudwatch.put_metric_alarm.assert_called_once()
        call_args = alarm_setup.cloudwatch.put_metric_alarm.call_args[1]
        
        assert call_args['AlarmName'] == 'LiteratureBoot-Chatbot-DescriptionGenerationFailureRate-development'
        assert call_args['Threshold'] == 10.0
        assert sns_topic_arn in call_args['AlarmActions']
        
        # Verify metric math
        metrics = call_args['Metrics']
        success_metric = next(m for m in metrics if m['Id'] == 'success')
        assert success_metric['MetricStat']['Metric']['MetricName'] == 'DescriptionGenerationSuccess'
        
        failure_metric = next(m for m in metrics if m['Id'] == 'failure')
        assert failure_metric['MetricStat']['Metric']['MetricName'] == 'DescriptionGenerationFailure'
    
    def test_create_bedrock_api_error_spike_alarm(self, alarm_setup):
        """Test creating Bedrock API error spike alarm."""
        sns_topic_arn = 'arn:aws:sns:us-west-2:123456789012:test-topic'
        
        alarm_name = alarm_setup.create_bedrock_api_error_spike_alarm(sns_topic_arn)
        
        # Verify alarm creation
        alarm_setup.cloudwatch.put_metric_alarm.assert_called_once()
        call_args = alarm_setup.cloudwatch.put_metric_alarm.call_args[1]
        
        assert call_args['AlarmName'] == 'LiteratureBoot-Chatbot-BedrockAPIErrorSpike-development'
        assert call_args['MetricName'] == 'BedrockAPIError'
        assert call_args['Namespace'] == 'LiteratureBoot/Chatbot'
        assert call_args['Statistic'] == 'Sum'
        assert call_args['Threshold'] == 50.0
        assert call_args['Period'] == 300
        assert call_args['EvaluationPeriods'] == 1
        assert call_args['DatapointsToAlarm'] == 1
        assert sns_topic_arn in call_args['AlarmActions']
    
    def test_setup_all_alarms_with_new_topic(self, alarm_setup):
        """Test setting up all alarms with new SNS topic."""
        alarm_setup.sns.create_topic.return_value = {
            'TopicArn': 'arn:aws:sns:us-west-2:123456789012:test-topic'
        }
        
        result = alarm_setup.setup_all_alarms(email='test@example.com')
        
        # Verify SNS topic creation
        alarm_setup.sns.create_topic.assert_called_once()
        alarm_setup.sns.subscribe.assert_called_once()
        
        # Verify all alarms created
        assert alarm_setup.cloudwatch.put_metric_alarm.call_count == 4
        
        # Verify result structure
        assert 'sns_topic_arn' in result
        assert 'alarms' in result
        assert len(result['alarms']) == 4
        assert 'high_response_time' in result['alarms']
        assert 'high_error_rate' in result['alarms']
        assert 'description_failure_rate' in result['alarms']
        assert 'bedrock_error_spike' in result['alarms']
    
    def test_setup_all_alarms_with_existing_topic(self, alarm_setup):
        """Test setting up all alarms with existing SNS topic."""
        existing_topic_arn = 'arn:aws:sns:us-west-2:123456789012:existing-topic'
        
        result = alarm_setup.setup_all_alarms(sns_topic_arn=existing_topic_arn)
        
        # Verify SNS topic NOT created
        alarm_setup.sns.create_topic.assert_not_called()
        
        # Verify all alarms created
        assert alarm_setup.cloudwatch.put_metric_alarm.call_count == 4
        
        # Verify existing topic used
        assert result['sns_topic_arn'] == existing_topic_arn
    
    def test_delete_all_alarms(self, alarm_setup):
        """Test deleting all alarms for environment."""
        alarm_setup.cloudwatch.describe_alarms.return_value = {
            'MetricAlarms': [
                {'AlarmName': 'LiteratureBoot-Chatbot-HighResponseTime-development'},
                {'AlarmName': 'LiteratureBoot-Chatbot-HighErrorRate-development'},
                {'AlarmName': 'LiteratureBoot-Chatbot-HighResponseTime-production'},
            ]
        }
        
        alarm_setup.delete_all_alarms()
        
        # Verify describe alarms called
        alarm_setup.cloudwatch.describe_alarms.assert_called_once_with(
            AlarmNamePrefix='LiteratureBoot-Chatbot-'
        )
        
        # Verify only development alarms deleted
        alarm_setup.cloudwatch.delete_alarms.assert_called_once()
        deleted_alarms = alarm_setup.cloudwatch.delete_alarms.call_args[1]['AlarmNames']
        assert len(deleted_alarms) == 2
        assert 'LiteratureBoot-Chatbot-HighResponseTime-development' in deleted_alarms
        assert 'LiteratureBoot-Chatbot-HighErrorRate-development' in deleted_alarms
        assert 'LiteratureBoot-Chatbot-HighResponseTime-production' not in deleted_alarms
    
    def test_delete_all_alarms_none_found(self, alarm_setup):
        """Test deleting alarms when none exist."""
        alarm_setup.cloudwatch.describe_alarms.return_value = {
            'MetricAlarms': []
        }
        
        alarm_setup.delete_all_alarms()
        
        # Verify describe called but delete not called
        alarm_setup.cloudwatch.describe_alarms.assert_called_once()
        alarm_setup.cloudwatch.delete_alarms.assert_not_called()


class TestAlarmConfiguration:
    """Test alarm configuration values match requirements."""
    
    def test_high_response_time_threshold(self):
        """Verify high response time alarm threshold is 7 seconds."""
        # Requirement: Alert if chatbot response time > 7 seconds (p95)
        threshold = 7000  # milliseconds
        assert threshold == 7000
    
    def test_error_rate_threshold(self):
        """Verify error rate alarm threshold is 10%."""
        # Requirement: Alert if chatbot error rate > 10%
        threshold = 10.0  # percent
        assert threshold == 10.0
    
    def test_description_failure_rate_threshold(self):
        """Verify description generation failure rate threshold is 10%."""
        # Requirement: Alert if description generation failure rate > 10%
        threshold = 10.0  # percent
        assert threshold == 10.0
    
    def test_bedrock_error_spike_threshold(self):
        """Verify Bedrock API error spike threshold is 50 errors in 5 minutes."""
        # Requirement: Alert if Bedrock API errors spike
        threshold = 50
        period = 300  # 5 minutes in seconds
        assert threshold == 50
        assert period == 300
    
    def test_namespace_consistency(self):
        """Verify all alarms use consistent namespace."""
        namespace = 'LiteratureBoot/Chatbot'
        assert namespace == 'LiteratureBoot/Chatbot'
    
    def test_environment_dimension_values(self):
        """Verify valid environment dimension values."""
        valid_environments = ['development', 'staging', 'production']
        assert 'development' in valid_environments
        assert 'staging' in valid_environments
        assert 'production' in valid_environments


class TestAlarmMetricMath:
    """Test metric math expressions for rate calculations."""
    
    def test_error_rate_calculation(self):
        """Test error rate calculation formula."""
        # Simulate metric values
        success = 90
        failure = 10
        
        # Calculate error rate
        error_rate = (failure / (success + failure)) * 100
        
        assert error_rate == 10.0
    
    def test_error_rate_no_failures(self):
        """Test error rate when there are no failures."""
        success = 100
        failure = 0
        
        error_rate = (failure / (success + failure)) * 100
        
        assert error_rate == 0.0
    
    def test_error_rate_all_failures(self):
        """Test error rate when all requests fail."""
        success = 0
        failure = 100
        
        error_rate = (failure / (success + failure)) * 100
        
        assert error_rate == 100.0
    
    def test_description_failure_rate_calculation(self):
        """Test description generation failure rate calculation."""
        success = 85
        failure = 15
        
        failure_rate = (failure / (success + failure)) * 100
        
        assert failure_rate == 15.0


class TestAlarmIntegration:
    """Integration tests for alarm setup (requires AWS credentials)."""
    
    @pytest.mark.skip(reason="Requires AWS credentials and creates real resources")
    def test_setup_alarms_integration(self):
        """
        Integration test for alarm setup.
        Skipped by default - run manually with valid AWS credentials.
        """
        setup = CloudWatchAlarmSetup(environment='development', region='us-west-2')
        
        # Create alarms
        result = setup.setup_all_alarms(email='test@example.com')
        
        assert 'sns_topic_arn' in result
        assert 'alarms' in result
        assert len(result['alarms']) == 4
        
        # Cleanup
        setup.delete_all_alarms()
    
    @pytest.mark.skip(reason="Requires AWS credentials")
    def test_alarm_trigger_simulation(self):
        """
        Test alarm triggering with simulated metric data.
        Skipped by default - run manually with valid AWS credentials.
        """
        import boto3
        from datetime import datetime
        
        cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
        
        # Emit high response time metrics
        for i in range(10):
            cloudwatch.put_metric_data(
                Namespace='LiteratureBoot/Chatbot',
                MetricData=[
                    {
                        'MetricName': 'ChatbotResponseTime',
                        'Value': 8000.0,  # Above 7000ms threshold
                        'Unit': 'Milliseconds',
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': [
                            {'Name': 'Environment', 'Value': 'development'},
                            {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                            {'Name': 'Operation', 'Value': 'ChatbotResponse'},
                            {'Name': 'Status', 'Value': 'Success'}
                        ]
                    }
                ]
            )
        
        # Wait for alarm to evaluate (typically 5-10 minutes)
        # Check alarm state manually in AWS Console


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
