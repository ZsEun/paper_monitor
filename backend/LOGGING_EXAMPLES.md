# Structured Logging Examples

## Example Log Output

### Successful Conversation Message

```json
{
  "event_type": "conversation_message_start",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "message_length": 45
}

{
  "event_type": "chatbot_response_success",
  "timestamp": "2024-01-15T10:30:02.345Z",
  "duration_ms": 2345,
  "status": "success",
  "conversation_length": 4,
  "should_conclude": false
}

{
  "event_type": "conversation_saved",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:30:02.456Z",
  "conversation_length": 4,
  "conversation_status": "in_progress"
}

{
  "event_type": "conversation_message_complete",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:30:02.500Z",
  "duration_ms": 2500,
  "status": "success",
  "conversation_status": "in_progress",
  "response_length": 156
}
```

### Timeout Event

```json
{
  "event_type": "conversation_message_start",
  "correlation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:35:00.000Z",
  "message_length": 32
}

{
  "event_type": "chatbot_response_timeout",
  "timestamp": "2024-01-15T10:35:05.100Z",
  "duration_ms": 5100,
  "status": "timeout",
  "error_message": "Chatbot response exceeded 5 second timeout"
}

{
  "event_type": "conversation_message_timeout",
  "correlation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:35:05.150Z",
  "duration_ms": 5150,
  "status": "timeout",
  "error_message": "Timeout"
}
```

### AI Service Error

```json
{
  "event_type": "conversation_message_start",
  "correlation_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:40:00.000Z",
  "message_length": 28
}

{
  "event_type": "chatbot_response_failed",
  "timestamp": "2024-01-15T10:40:01.234Z",
  "duration_ms": 1234,
  "status": "failed",
  "error_type": "bedrock_api_error",
  "error_code": "ThrottlingException"
}

{
  "event_type": "conversation_message_failed",
  "correlation_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:40:01.250Z",
  "duration_ms": 1250,
  "status": "failed",
  "error_type": "ai_service_error",
  "error_message": "AWS Bedrock API error: ThrottlingException"
}
```

### Description Generation

```json
{
  "event_type": "description_generation_start",
  "correlation_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:45:00.000Z",
  "input_length": 1234
}

{
  "event_type": "description_generation_start",
  "timestamp": "2024-01-15T10:45:00.050Z",
  "conversation_length": 12
}

{
  "event_type": "description_generation_complete",
  "timestamp": "2024-01-15T10:45:03.456Z",
  "duration_ms": 3406,
  "status": "success",
  "input_length": 567,
  "output_length": 1234
}

{
  "event_type": "description_saved",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:45:03.500Z",
  "description_length": 1234
}

{
  "event_type": "description_generation_complete",
  "correlation_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:45:03.550Z",
  "duration_ms": 3550,
  "status": "success",
  "output_length": 1234
}
```

### Conversation Cancellation

```json
{
  "event_type": "conversation_cancelled",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:50:00.000Z"
}

{
  "event_type": "conversation_reset",
  "user_id": "user-uuid-123",
  "topic_id": "topic-uuid-456",
  "timestamp": "2024-01-15T10:50:00.123Z"
}
```

## CloudWatch Logs Insights Queries

### Monitor Response Times

```
fields @timestamp, duration_ms, conversation_status
| filter event_type = "conversation_message_complete"
| stats avg(duration_ms) as avg_response_time, 
        max(duration_ms) as max_response_time,
        count() as total_messages
  by bin(5m)
| sort @timestamp desc
```

### Track Error Rates

```
fields @timestamp, error_type, error_message
| filter event_type like /failed/
| stats count() as error_count by error_type, bin(1h)
| sort error_count desc
```

### Trace Specific Request

```
fields @timestamp, event_type, status, duration_ms, error_message
| filter correlation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
| sort @timestamp asc
```

### Monitor Timeout Rate

```
fields @timestamp
| filter event_type = "conversation_message_timeout"
| stats count() as timeout_count by bin(1h)
```

### Track Description Generation Performance

```
fields @timestamp, duration_ms, input_length, output_length
| filter event_type = "description_generation_complete"
| stats avg(duration_ms) as avg_duration,
        avg(input_length) as avg_input,
        avg(output_length) as avg_output
  by bin(1h)
```

### Monitor Conversation Completion Rate

```
fields @timestamp, conversation_status
| filter event_type = "conversation_message_complete"
| stats count() as total_messages,
        sum(case when conversation_status = "completed" then 1 else 0 end) as completed_conversations
  by bin(1d)
```

### User Activity Analysis

```
fields @timestamp, user_id, topic_id
| filter event_type = "conversation_message_start"
| stats count() as message_count by user_id
| sort message_count desc
| limit 20
```

## Privacy Compliance

Note that all logs contain only metadata (lengths, counts, IDs) and do NOT include:
- User message content
- Chatbot response content
- Conversation history content
- Comprehensive description content

This ensures user privacy while maintaining full observability for monitoring and debugging.
