#!/usr/bin/env python3
"""
Task 16.3 Validation Script

Validates that CloudWatch alarms are configured according to task requirements:
- Alert if chatbot response time > 7 seconds (p95)
- Alert if chatbot error rate > 10%
- Alert if description generation failure rate > 10%
- Alert if Bedrock API errors spike
"""

import sys


def validate_cloudformation_template():
    """Validate CloudFormation template has all required alarms."""
    print("Validating CloudFormation template...")
    
    with open('cloudwatch-alarms.yaml', 'r') as f:
        content = f.read()
    
    # Check all required alarms exist
    required_alarms = [
        'HighResponseTimeAlarm',
        'HighErrorRateAlarm',
        'DescriptionGenerationFailureRateAlarm',
        'BedrockAPIErrorSpikeAlarm'
    ]
    
    for alarm_name in required_alarms:
        if alarm_name not in content:
            print(f"❌ FAIL: Missing alarm: {alarm_name}")
            return False
        print(f"✅ Found alarm: {alarm_name}")
    
    # Validate High Response Time Alarm configuration
    assert 'MetricName: ChatbotResponseTime' in content, "Wrong metric name"
    assert 'ExtendedStatistic: p95' in content, "Should use p95 statistic"
    assert 'Threshold: 7000' in content, "Threshold should be 7000ms (7 seconds)"
    print("✅ High Response Time Alarm: p95 > 7 seconds")
    
    # Validate High Error Rate Alarm
    assert "Expression: '(failure / (success + failure)) * 100'" in content, "Wrong error rate formula"
    assert 'Threshold: 10  # 10%' in content, "Error rate threshold should be 10%"
    print("✅ High Error Rate Alarm: error rate > 10%")
    
    # Validate Description Generation Failure Rate Alarm
    assert 'DescriptionGenerationSuccess' in content, "Missing DescriptionGenerationSuccess metric"
    assert 'DescriptionGenerationFailure' in content, "Missing DescriptionGenerationFailure metric"
    print("✅ Description Generation Failure Rate Alarm: failure rate > 10%")
    
    # Validate Bedrock API Error Spike Alarm
    assert 'MetricName: BedrockAPIError' in content, "Wrong metric name for Bedrock alarm"
    assert 'Threshold: 50' in content, "Bedrock error threshold should be 50"
    assert 'Period: 300  # 5 minutes' in content, "Period should be 5 minutes"
    print("✅ Bedrock API Error Spike Alarm: > 50 errors in 5 minutes")
    
    # Validate SNS topic configuration
    assert 'ChatbotAlarmTopic' in content, "Missing SNS topic"
    print("✅ SNS topic configured for notifications")
    
    # Validate parameters
    assert 'Parameters:' in content, "Missing parameters section"
    assert 'Environment:' in content, "Missing Environment parameter"
    assert 'AlarmEmail:' in content, "Missing AlarmEmail parameter"
    print("✅ Template parameters configured correctly")
    
    return True


def validate_python_script():
    """Validate Python script has all required alarm creation methods."""
    print("\nValidating Python script...")
    
    with open('setup_cloudwatch_alarms.py', 'r') as f:
        content = f.read()
    
    # Check all required methods exist
    required_methods = [
        'create_high_response_time_alarm',
        'create_high_error_rate_alarm',
        'create_description_generation_failure_rate_alarm',
        'create_bedrock_api_error_spike_alarm',
        'setup_all_alarms'
    ]
    
    for method in required_methods:
        if f'def {method}' not in content:
            print(f"❌ FAIL: Missing method: {method}")
            return False
        print(f"✅ Found method: {method}")
    
    # Check threshold values in code
    assert 'Threshold=7000.0' in content, "High response time threshold should be 7000ms"
    print("✅ High response time threshold: 7000ms")
    
    assert 'Threshold=10.0' in content, "Error rate threshold should be 10%"
    print("✅ Error rate threshold: 10%")
    
    assert 'Threshold=50.0' in content, "Bedrock error spike threshold should be 50"
    print("✅ Bedrock error spike threshold: 50 errors")
    
    # Check metric math expressions
    assert "'(failure / (success + failure)) * 100'" in content, "Missing error rate calculation"
    print("✅ Error rate calculation formula correct")
    
    return True


def validate_documentation():
    """Validate documentation files exist and contain required information."""
    print("\nValidating documentation...")
    
    required_files = [
        'CLOUDWATCH_ALARMS.md',
        'ALARM_SETUP_GUIDE.md',
        'ALARM_DEPLOYMENT_SUMMARY.md'
    ]
    
    for filename in required_files:
        try:
            with open(filename, 'r') as f:
                content = f.read()
            print(f"✅ Found documentation: {filename}")
            
            # Check for key sections
            if filename == 'CLOUDWATCH_ALARMS.md':
                assert 'High Response Time' in content, "Missing High Response Time section"
                assert 'High Error Rate' in content, "Missing High Error Rate section"
                assert 'Description Generation Failure' in content, "Missing Description Generation section"
                assert 'Bedrock API Error Spike' in content, "Missing Bedrock API Error section"
                print("  ✅ All alarm sections documented")
        
        except FileNotFoundError:
            print(f"❌ FAIL: Missing documentation file: {filename}")
            return False
    
    return True


def validate_tests():
    """Validate test file exists and covers alarm configuration."""
    print("\nValidating tests...")
    
    try:
        with open('test_cloudwatch_alarms.py', 'r') as f:
            content = f.read()
        
        # Check test classes exist
        assert 'class TestCloudWatchAlarmSetup' in content, "Missing alarm setup tests"
        assert 'class TestAlarmConfiguration' in content, "Missing configuration tests"
        assert 'class TestAlarmMetricMath' in content, "Missing metric math tests"
        print("✅ Test classes found")
        
        # Check specific test methods
        required_tests = [
            'test_create_high_response_time_alarm',
            'test_create_high_error_rate_alarm',
            'test_create_description_generation_failure_rate_alarm',
            'test_create_bedrock_api_error_spike_alarm',
            'test_setup_all_alarms'
        ]
        
        for test in required_tests:
            if f'def {test}' not in content:
                print(f"❌ FAIL: Missing test: {test}")
                return False
            print(f"✅ Found test: {test}")
        
        return True
    
    except FileNotFoundError:
        print("❌ FAIL: Missing test file: test_cloudwatch_alarms.py")
        return False


def main():
    """Run all validations."""
    print("="*70)
    print("Task 16.3 Validation: Configure CloudWatch Alarms")
    print("="*70)
    
    all_passed = True
    
    # Run validations
    try:
        if not validate_cloudformation_template():
            all_passed = False
    except Exception as e:
        print(f"❌ CloudFormation validation failed: {e}")
        all_passed = False
    
    try:
        if not validate_python_script():
            all_passed = False
    except Exception as e:
        print(f"❌ Python script validation failed: {e}")
        all_passed = False
    
    try:
        if not validate_documentation():
            all_passed = False
    except Exception as e:
        print(f"❌ Documentation validation failed: {e}")
        all_passed = False
    
    try:
        if not validate_tests():
            all_passed = False
    except Exception as e:
        print(f"❌ Test validation failed: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ TASK 16.3 VALIDATION PASSED")
        print("="*70)
        print("\nAll required alarms are configured:")
        print("  ✅ Alert if chatbot response time > 7 seconds (p95)")
        print("  ✅ Alert if chatbot error rate > 10%")
        print("  ✅ Alert if description generation failure rate > 10%")
        print("  ✅ Alert if Bedrock API errors spike")
        print("\nDeployment options available:")
        print("  • CloudFormation template (cloudwatch-alarms.yaml)")
        print("  • Python script (setup_cloudwatch_alarms.py)")
        print("  • AWS CDK (cloudwatch_alarms_cdk.py)")
        print("\nSee ALARM_SETUP_GUIDE.md for deployment instructions.")
        return 0
    else:
        print("❌ TASK 16.3 VALIDATION FAILED")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
