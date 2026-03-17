#!/usr/bin/env python3
"""
CloudWatch Alarms Setup Script

Creates CloudWatch alarms for monitoring the Interest Definition Chatbot.
Can be run as a standalone script or imported as a module.

Usage:
    python setup_cloudwatch_alarms.py --environment production --email alerts@example.com
    python setup_cloudwatch_alarms.py --environment staging --sns-topic-arn arn:aws:sns:us-west-2:123456789012:my-topic
"""

import boto3
import argparse
import logging
from typing import Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CloudWatchAlarmSetup:
    """
    Sets up CloudWatch alarms for the Interest Definition Chatbot.
    """
    
    def __init__(self, environment: str = 'production', region: str = 'us-west-2'):
        """
        Initialize CloudWatch alarm setup.
        
        Args:
            environment: Deployment environment (development, staging, production)
            region: AWS region
        """
        self.environment = environment
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.namespace = 'LiteratureBoot/Chatbot'
    
    def create_sns_topic(self, email: Optional[str] = None) -> str:
        """
        Create SNS topic for alarm notifications.
        
        Args:
            email: Optional email address to subscribe to the topic
            
        Returns:
            SNS topic ARN
        """
        topic_name = f'literature-boot-chatbot-alarms-{self.environment}'
        
        try:
            # Create topic
            response = self.sns.create_topic(Name=topic_name)
            topic_arn = response['TopicArn']
            logger.info(f"Created SNS topic: {topic_arn}")
            
            # Subscribe email if provided
            if email:
                self.sns.subscribe(
                    TopicArn=topic_arn,
                    Protocol='email',
                    Endpoint=email
                )
                logger.info(f"Subscribed {email} to SNS topic (confirmation email sent)")
            
            return topic_arn
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'TopicAlreadyExists':
                # Get existing topic ARN
                response = self.sns.create_topic(Name=topic_name)
                topic_arn = response['TopicArn']
                logger.info(f"Using existing SNS topic: {topic_arn}")
                return topic_arn
            else:
                raise
    
    def create_high_response_time_alarm(self, sns_topic_arn: str) -> str:
        """
        Create alarm for high chatbot response time (p95 > 7 seconds).
        
        Args:
            sns_topic_arn: SNS topic ARN for notifications
            
        Returns:
            Alarm ARN
        """
        alarm_name = f'LiteratureBoot-Chatbot-HighResponseTime-{self.environment}'
        
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription='Alert when chatbot response time p95 exceeds 7 seconds',
                ActionsEnabled=True,
                AlarmActions=[sns_topic_arn],
                MetricName='ChatbotResponseTime',
                Namespace=self.namespace,
                Statistic='Average',
                ExtendedStatistic='p95',
                Dimensions=[
                    {'Name': 'Environment', 'Value': self.environment},
                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                    {'Name': 'Operation', 'Value': 'ChatbotResponse'},
                    {'Name': 'Status', 'Value': 'Success'}
                ],
                Period=300,  # 5 minutes
                EvaluationPeriods=2,
                DatapointsToAlarm=2,
                Threshold=7000.0,  # 7 seconds in milliseconds
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching'
            )
            logger.info(f"Created alarm: {alarm_name}")
            return alarm_name
        
        except ClientError as e:
            logger.error(f"Failed to create alarm {alarm_name}: {e}")
            raise
    
    def create_high_error_rate_alarm(self, sns_topic_arn: str) -> str:
        """
        Create alarm for high chatbot error rate (> 10%).
        Uses metric math to calculate error rate percentage.
        
        Args:
            sns_topic_arn: SNS topic ARN for notifications
            
        Returns:
            Alarm ARN
        """
        alarm_name = f'LiteratureBoot-Chatbot-HighErrorRate-{self.environment}'
        
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription='Alert when chatbot error rate exceeds 10%',
                ActionsEnabled=True,
                AlarmActions=[sns_topic_arn],
                Metrics=[
                    {
                        'Id': 'success',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': self.namespace,
                                'MetricName': 'ChatbotSuccess',
                                'Dimensions': [
                                    {'Name': 'Environment', 'Value': self.environment},
                                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                                    {'Name': 'Operation', 'Value': 'ChatbotResponse'}
                                ]
                            },
                            'Period': 300,  # 5 minutes
                            'Stat': 'Sum'
                        },
                        'ReturnData': False
                    },
                    {
                        'Id': 'failure',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': self.namespace,
                                'MetricName': 'ChatbotFailure',
                                'Dimensions': [
                                    {'Name': 'Environment', 'Value': self.environment},
                                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                                    {'Name': 'Operation', 'Value': 'ChatbotResponse'}
                                ]
                            },
                            'Period': 300,  # 5 minutes
                            'Stat': 'Sum'
                        },
                        'ReturnData': False
                    },
                    {
                        'Id': 'error_rate',
                        'Expression': '(failure / (success + failure)) * 100',
                        'Label': 'Error Rate Percentage',
                        'ReturnData': True
                    }
                ],
                EvaluationPeriods=2,
                DatapointsToAlarm=2,
                Threshold=10.0,  # 10%
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching'
            )
            logger.info(f"Created alarm: {alarm_name}")
            return alarm_name
        
        except ClientError as e:
            logger.error(f"Failed to create alarm {alarm_name}: {e}")
            raise
    
    def create_description_generation_failure_rate_alarm(self, sns_topic_arn: str) -> str:
        """
        Create alarm for high description generation failure rate (> 10%).
        Uses metric math to calculate failure rate percentage.
        
        Args:
            sns_topic_arn: SNS topic ARN for notifications
            
        Returns:
            Alarm ARN
        """
        alarm_name = f'LiteratureBoot-Chatbot-DescriptionGenerationFailureRate-{self.environment}'
        
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription='Alert when description generation failure rate exceeds 10%',
                ActionsEnabled=True,
                AlarmActions=[sns_topic_arn],
                Metrics=[
                    {
                        'Id': 'success',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': self.namespace,
                                'MetricName': 'DescriptionGenerationSuccess',
                                'Dimensions': [
                                    {'Name': 'Environment', 'Value': self.environment},
                                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                                    {'Name': 'Operation', 'Value': 'DescriptionGeneration'}
                                ]
                            },
                            'Period': 300,  # 5 minutes
                            'Stat': 'Sum'
                        },
                        'ReturnData': False
                    },
                    {
                        'Id': 'failure',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': self.namespace,
                                'MetricName': 'DescriptionGenerationFailure',
                                'Dimensions': [
                                    {'Name': 'Environment', 'Value': self.environment},
                                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                                    {'Name': 'Operation', 'Value': 'DescriptionGeneration'}
                                ]
                            },
                            'Period': 300,  # 5 minutes
                            'Stat': 'Sum'
                        },
                        'ReturnData': False
                    },
                    {
                        'Id': 'failure_rate',
                        'Expression': '(failure / (success + failure)) * 100',
                        'Label': 'Description Generation Failure Rate Percentage',
                        'ReturnData': True
                    }
                ],
                EvaluationPeriods=2,
                DatapointsToAlarm=2,
                Threshold=10.0,  # 10%
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching'
            )
            logger.info(f"Created alarm: {alarm_name}")
            return alarm_name
        
        except ClientError as e:
            logger.error(f"Failed to create alarm {alarm_name}: {e}")
            raise
    
    def create_bedrock_api_error_spike_alarm(self, sns_topic_arn: str) -> str:
        """
        Create alarm for Bedrock API error spike (> 50 errors in 5 minutes).
        
        Args:
            sns_topic_arn: SNS topic ARN for notifications
            
        Returns:
            Alarm ARN
        """
        alarm_name = f'LiteratureBoot-Chatbot-BedrockAPIErrorSpike-{self.environment}'
        
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription='Alert when Bedrock API errors exceed 50 in 5 minutes',
                ActionsEnabled=True,
                AlarmActions=[sns_topic_arn],
                MetricName='BedrockAPIError',
                Namespace=self.namespace,
                Statistic='Sum',
                Dimensions=[
                    {'Name': 'Environment', 'Value': self.environment},
                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'}
                ],
                Period=300,  # 5 minutes
                EvaluationPeriods=1,
                DatapointsToAlarm=1,
                Threshold=50.0,
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching'
            )
            logger.info(f"Created alarm: {alarm_name}")
            return alarm_name
        
        except ClientError as e:
            logger.error(f"Failed to create alarm {alarm_name}: {e}")
            raise
    
    def setup_all_alarms(
        self,
        sns_topic_arn: Optional[str] = None,
        email: Optional[str] = None
    ) -> dict:
        """
        Create all CloudWatch alarms for the chatbot.
        
        Args:
            sns_topic_arn: Optional existing SNS topic ARN. If not provided, creates new topic.
            email: Optional email address for alarm notifications
            
        Returns:
            Dictionary with alarm names and SNS topic ARN
        """
        # Create or use existing SNS topic
        if sns_topic_arn:
            logger.info(f"Using existing SNS topic: {sns_topic_arn}")
            topic_arn = sns_topic_arn
        else:
            logger.info("Creating new SNS topic for alarm notifications")
            topic_arn = self.create_sns_topic(email)
        
        # Create all alarms
        alarms = {}
        
        logger.info("Creating High Response Time alarm...")
        alarms['high_response_time'] = self.create_high_response_time_alarm(topic_arn)
        
        logger.info("Creating High Error Rate alarm...")
        alarms['high_error_rate'] = self.create_high_error_rate_alarm(topic_arn)
        
        logger.info("Creating Description Generation Failure Rate alarm...")
        alarms['description_failure_rate'] = self.create_description_generation_failure_rate_alarm(topic_arn)
        
        logger.info("Creating Bedrock API Error Spike alarm...")
        alarms['bedrock_error_spike'] = self.create_bedrock_api_error_spike_alarm(topic_arn)
        
        logger.info(f"Successfully created {len(alarms)} CloudWatch alarms")
        
        return {
            'sns_topic_arn': topic_arn,
            'alarms': alarms
        }
    
    def delete_all_alarms(self) -> None:
        """
        Delete all chatbot-related CloudWatch alarms for this environment.
        Useful for cleanup or redeployment.
        """
        alarm_prefix = f'LiteratureBoot-Chatbot-'
        
        try:
            # List all alarms with our prefix
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=alarm_prefix
            )
            
            alarm_names = [alarm['AlarmName'] for alarm in response['MetricAlarms']]
            
            # Filter by environment
            env_alarms = [name for name in alarm_names if name.endswith(f'-{self.environment}')]
            
            if not env_alarms:
                logger.info(f"No alarms found for environment: {self.environment}")
                return
            
            # Delete alarms
            self.cloudwatch.delete_alarms(AlarmNames=env_alarms)
            logger.info(f"Deleted {len(env_alarms)} alarms: {', '.join(env_alarms)}")
        
        except ClientError as e:
            logger.error(f"Failed to delete alarms: {e}")
            raise


def main():
    """
    Main entry point for CLI usage.
    """
    parser = argparse.ArgumentParser(
        description='Setup CloudWatch alarms for Interest Definition Chatbot'
    )
    parser.add_argument(
        '--environment',
        type=str,
        default='production',
        choices=['development', 'staging', 'production'],
        help='Deployment environment'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-west-2',
        help='AWS region'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='Email address for alarm notifications'
    )
    parser.add_argument(
        '--sns-topic-arn',
        type=str,
        help='Existing SNS topic ARN (if not provided, creates new topic)'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete all alarms instead of creating them'
    )
    
    args = parser.parse_args()
    
    # Initialize setup
    setup = CloudWatchAlarmSetup(
        environment=args.environment,
        region=args.region
    )
    
    if args.delete:
        # Delete alarms
        logger.info(f"Deleting alarms for environment: {args.environment}")
        setup.delete_all_alarms()
    else:
        # Create alarms
        logger.info(f"Setting up alarms for environment: {args.environment}")
        result = setup.setup_all_alarms(
            sns_topic_arn=args.sns_topic_arn,
            email=args.email
        )
        
        print("\n" + "="*60)
        print("CloudWatch Alarms Setup Complete")
        print("="*60)
        print(f"SNS Topic ARN: {result['sns_topic_arn']}")
        print(f"\nCreated Alarms:")
        for alarm_type, alarm_name in result['alarms'].items():
            print(f"  - {alarm_name}")
        
        if args.email:
            print(f"\nConfirmation email sent to: {args.email}")
            print("Please check your email and confirm the subscription.")
        
        print("\nYou can view alarms in the AWS Console:")
        print(f"https://console.aws.amazon.com/cloudwatch/home?region={args.region}#alarmsV2:")


if __name__ == '__main__':
    main()
