"""
AWS CDK Stack for CloudWatch Alarms

Alternative to CloudFormation template for teams using AWS CDK.
Defines CloudWatch alarms for Interest Definition Chatbot monitoring.

Usage:
    from cloudwatch_alarms_cdk import ChatbotAlarmsStack
    
    app = cdk.App()
    ChatbotAlarmsStack(app, "ChatbotAlarms",
        environment="production",
        alarm_email="alerts@example.com"
    )
    app.synth()
"""

from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    Duration,
)
from constructs import Construct
from typing import Optional


class ChatbotAlarmsStack(Stack):
    """
    CDK Stack for Interest Definition Chatbot CloudWatch Alarms.
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "production",
        alarm_email: Optional[str] = None,
        sns_topic_arn: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Initialize the CloudWatch alarms stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            environment: Deployment environment (development, staging, production)
            alarm_email: Optional email address for alarm notifications
            sns_topic_arn: Optional existing SNS topic ARN
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        self.namespace = "LiteratureBoot/Chatbot"
        
        # Create or import SNS topic
        if sns_topic_arn:
            self.alarm_topic = sns.Topic.from_topic_arn(
                self, "AlarmTopic", sns_topic_arn
            )
        else:
            self.alarm_topic = sns.Topic(
                self, "ChatbotAlarmTopic",
                topic_name=f"literature-boot-chatbot-alarms-{environment}",
                display_name="Literature Boot Chatbot Alarms"
            )
            
            # Subscribe email if provided
            if alarm_email:
                self.alarm_topic.add_subscription(
                    subscriptions.EmailSubscription(alarm_email)
                )
        
        # Create alarms
        self.create_high_response_time_alarm()
        self.create_high_error_rate_alarm()
        self.create_description_generation_failure_rate_alarm()
        self.create_bedrock_api_error_spike_alarm()
    
    def create_high_response_time_alarm(self) -> cloudwatch.Alarm:
        """
        Create alarm for high chatbot response time (p95 > 7 seconds).
        
        Returns:
            CloudWatch Alarm
        """
        metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="ChatbotResponseTime",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot",
                "Operation": "ChatbotResponse",
                "Status": "Success"
            },
            statistic="p95",
            period=Duration.minutes(5)
        )
        
        alarm = cloudwatch.Alarm(
            self, "HighResponseTimeAlarm",
            alarm_name=f"LiteratureBoot-Chatbot-HighResponseTime-{self.environment}",
            alarm_description="Alert when chatbot response time p95 exceeds 7 seconds",
            metric=metric,
            threshold=7000.0,  # 7 seconds in milliseconds
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        
        return alarm
    
    def create_high_error_rate_alarm(self) -> cloudwatch.Alarm:
        """
        Create alarm for high chatbot error rate (> 10%).
        Uses metric math to calculate error rate percentage.
        
        Returns:
            CloudWatch Alarm
        """
        success_metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="ChatbotSuccess",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot",
                "Operation": "ChatbotResponse"
            },
            statistic="Sum",
            period=Duration.minutes(5)
        )
        
        failure_metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="ChatbotFailure",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot",
                "Operation": "ChatbotResponse"
            },
            statistic="Sum",
            period=Duration.minutes(5)
        )
        
        # Calculate error rate using metric math
        error_rate = cloudwatch.MathExpression(
            expression="(failure / (success + failure)) * 100",
            using_metrics={
                "success": success_metric,
                "failure": failure_metric
            },
            label="Error Rate Percentage",
            period=Duration.minutes(5)
        )
        
        alarm = cloudwatch.Alarm(
            self, "HighErrorRateAlarm",
            alarm_name=f"LiteratureBoot-Chatbot-HighErrorRate-{self.environment}",
            alarm_description="Alert when chatbot error rate exceeds 10%",
            metric=error_rate,
            threshold=10.0,  # 10%
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        
        return alarm
    
    def create_description_generation_failure_rate_alarm(self) -> cloudwatch.Alarm:
        """
        Create alarm for high description generation failure rate (> 10%).
        Uses metric math to calculate failure rate percentage.
        
        Returns:
            CloudWatch Alarm
        """
        success_metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="DescriptionGenerationSuccess",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot",
                "Operation": "DescriptionGeneration"
            },
            statistic="Sum",
            period=Duration.minutes(5)
        )
        
        failure_metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="DescriptionGenerationFailure",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot",
                "Operation": "DescriptionGeneration"
            },
            statistic="Sum",
            period=Duration.minutes(5)
        )
        
        # Calculate failure rate using metric math
        failure_rate = cloudwatch.MathExpression(
            expression="(failure / (success + failure)) * 100",
            using_metrics={
                "success": success_metric,
                "failure": failure_metric
            },
            label="Description Generation Failure Rate Percentage",
            period=Duration.minutes(5)
        )
        
        alarm = cloudwatch.Alarm(
            self, "DescriptionGenerationFailureRateAlarm",
            alarm_name=f"LiteratureBoot-Chatbot-DescriptionGenerationFailureRate-{self.environment}",
            alarm_description="Alert when description generation failure rate exceeds 10%",
            metric=failure_rate,
            threshold=10.0,  # 10%
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        
        return alarm
    
    def create_bedrock_api_error_spike_alarm(self) -> cloudwatch.Alarm:
        """
        Create alarm for Bedrock API error spike (> 50 errors in 5 minutes).
        
        Returns:
            CloudWatch Alarm
        """
        metric = cloudwatch.Metric(
            namespace=self.namespace,
            metric_name="BedrockAPIError",
            dimensions_map={
                "Environment": self.environment,
                "Service": "InterestDefinitionChatbot"
            },
            statistic="Sum",
            period=Duration.minutes(5)
        )
        
        alarm = cloudwatch.Alarm(
            self, "BedrockAPIErrorSpikeAlarm",
            alarm_name=f"LiteratureBoot-Chatbot-BedrockAPIErrorSpike-{self.environment}",
            alarm_description="Alert when Bedrock API errors exceed 50 in 5 minutes",
            metric=metric,
            threshold=50.0,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        
        return alarm


# Example usage in CDK app
if __name__ == "__main__":
    import aws_cdk as cdk
    
    app = cdk.App()
    
    # Create stack for production environment
    ChatbotAlarmsStack(
        app, "LiteratureBootChatbotAlarmsProd",
        environment="production",
        alarm_email="alerts@example.com",
        env=cdk.Environment(region="us-west-2")
    )
    
    app.synth()
