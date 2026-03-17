# Structured Logging Implementation for Chatbot Interactions

## Overview

Implemented structured logging for all chatbot interactions using AWS CloudWatch Logs compatible JSON format. All logs include correlation IDs for request tracing and do NOT log full conversation content for privacy.

## Log Events

### Conversation Message Events

**conversation_message_start**
- Level: INFO
- Logged when: User sends a message to chatbot
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, message_length

**conversation_message_complete**
- Level: INFO
- Logged when: Chatbot successfully responds
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, duration_ms, status, conversation_status, response_length

**conversation_message_timeout**
- Level: WARNING
- Logged when: Chatbot response exceeds 5 seconds
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, duration_ms, status, error_message

**conversation_message_failed**
- Level: ERROR
- Logged when: Chatbot fails to respond (AI service error, unexpected error, not found)
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, duration_ms, status, error_type, error_message

### Conversation State Events

**conversation_cancelled**
- Level: INFO
- Logged when: User resets/cancels conversation
- Fields: event_type, user_id, topic_id, timestamp

**conversation_reset_failed**
- Level: ERROR
- Logged when: Conversation reset fails
- Fields: event_type, user_id, topic_id, timestamp, error_message

**conversation_saved**
- Level: INFO
- Logged when: Conversation state saved successfully
- Fields: event_type, user_id, topic_id, timestamp, conversation_length, conversation_status

**conversation_save_failed**
- Level: ERROR
- Logged when: Conversation save fails
- Fields: event_type, user_id, topic_id, timestamp, error_type, error_message

### Description Generation Events

**description_generation_start**
- Level: INFO
- Logged when: Description generation begins
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, input_length (for API endpoint) OR conversation_length (for service)

**description_generation_complete**
- Level: INFO
- Logged when: Description generated successfully
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, duration_ms, status, output_length (and input_length for service)

**description_generation_failed**
- Level: ERROR
- Logged when: Description generation fails
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, duration_ms, status, error_type, error_message

**description_validation_failed**
- Level: WARNING
- Logged when: Description validation fails (empty, too long)
- Fields: event_type, correlation_id, user_id, topic_id, timestamp, error_type, description_length (if applicable)

**description_saved**
- Level: INFO
- Logged when: Description saved successfully
- Fields: event_type, user_id, topic_id, timestamp, description_length

**description_save_failed**
- Level: ERROR
- Logged when: Description save fails
- Fields: event_type, user_id, topic_id, timestamp, error_type, error_message

### Chatbot Service Events

**chatbot_response_success**
- Level: INFO
- Logged when: ChatbotService successfully generates response
- Fields: event_type, timestamp, duration_ms, status, conversation_length, should_conclude

**chatbot_response_timeout**
- Level: WARNING
- Logged when: ChatbotService times out
- Fields: event_type, timestamp, duration_ms, status, error_message

**chatbot_response_failed**
- Level: ERROR
- Logged when: ChatbotService fails
- Fields: event_type, timestamp, duration_ms, status, error_type, error_code (if Bedrock error), error_message

## Privacy Compliance

✅ Logs do NOT include:
- Full message content (user or assistant)
- Conversation history content
- Comprehensive description content

✅ Logs DO include:
- Message/response lengths (metadata)
- Conversation length (count of messages)
- Description length (character count)
- Correlation IDs for tracing
- User IDs and topic IDs
- Timestamps and durations
- Status and error information

## Correlation ID Tracing

Each API request generates a unique correlation ID (UUID) that is included in all log events for that request. This enables:
- End-to-end request tracing
- Performance analysis
- Error debugging
- Request flow visualization in CloudWatch Insights

## CloudWatch Logs Integration

All logs are formatted as JSON for easy parsing in CloudWatch Logs Insights. Example queries:

```
# Find all timeout events
fields @timestamp, user_id, topic_id, duration_ms
| filter event_type = "conversation_message_timeout"
| sort @timestamp desc

# Track response times
fields @timestamp, duration_ms, conversation_status
| filter event_type = "conversation_message_complete"
| stats avg(duration_ms), max(duration_ms), count() by bin(5m)

# Trace a specific request
fields @timestamp, event_type, status, duration_ms
| filter correlation_id = "your-correlation-id-here"
| sort @timestamp asc

# Monitor error rates
fields @timestamp, error_type
| filter event_type like /failed/
| stats count() by error_type, bin(5m)
```

## Testing

All logging functionality is tested in `test_chatbot_logging.py`:
- ✅ Conversation start logging
- ✅ Conversation completion logging with duration
- ✅ Timeout logging
- ✅ AI service error logging
- ✅ Conversation cancellation logging
- ✅ Description generation logging with lengths
- ✅ Response time logging
- ✅ Privacy compliance (no content in logs)
- ✅ Correlation ID consistency
- ✅ Validation failure logging

All 13 tests pass successfully.
