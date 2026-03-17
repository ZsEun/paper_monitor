"""
Chatbot Service

Manages AI-powered conversations for defining research interests.
Uses AWS Bedrock Claude for natural language processing.

Set USE_MOCK_CHATBOT=true in environment to use local mock responses
(useful for development without AWS credentials).
"""

import boto3
import json
import logging
import os
import time
from typing import List, Dict
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError
from app.models.schemas import Message, ChatbotResponse, ConversationStatus
from app.services.metrics_service import get_metrics_service

# Configure logging
logger = logging.getLogger(__name__)

# Check if mock mode is enabled (for local development without AWS credentials)
USE_MOCK_CHATBOT = os.environ.get("USE_MOCK_CHATBOT", "false").lower() in ("true", "1", "yes")


class ChatbotService:
    """
    Manages AI-powered conversations for defining research interests.
    Uses AWS Bedrock Claude for natural language processing.
    """
    
    def __init__(self):
        self.mock_mode = USE_MOCK_CHATBOT

        if not self.mock_mode:
            # Chat client: short timeout for quick conversational responses
            chat_config = Config(
                read_timeout=5,
                connect_timeout=5,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                }
            )
            self.bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name='us-west-2',
                config=chat_config
            )
            
            # Description generation client: longer timeout for processing
            # full conversation transcripts and producing detailed output
            gen_config = Config(
                read_timeout=60,
                connect_timeout=10,
                retries={
                    'max_attempts': 2,
                    'mode': 'adaptive'
                }
            )
            self.bedrock_gen = boto3.client(
                service_name='bedrock-runtime',
                region_name='us-west-2',
                config=gen_config
            )
        else:
            self.bedrock = None
            self.bedrock_gen = None
            logger.info("ChatbotService running in MOCK mode (USE_MOCK_CHATBOT=true)")
        
        # Use Claude 3 Sonnet model
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        
        # System prompt that establishes chatbot personality and conversation flow
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """
        Create system prompt that establishes helpful, academic personality
        and guides conversation through 4 key areas with a structured
        selection-based flow.
        
        Requirements: 8.2, 8.3, 8.4, 8.5, 8.6
        """
        return """You are a helpful research assistant helping academics define their research interests. You guide users through a structured 4-step process. Follow these steps EXACTLY in order:

**STEP 1 — Aspects** (sub-topics):
- Based on the user's research topic, list exactly 5 specific sub-topics or aspects as a numbered list (1-5).
- Ask the user to pick the ones they're interested in (they can pick multiple, e.g. "1, 3, 5").
- After they choose, ask: "Would you like to explore more sub-topics, or shall we move on to research methods?"
- If they want more, list 5 more sub-topics and repeat. If they want to move on, go to Step 2.
- REMEMBER which sub-topics the user chose and which they did NOT choose — you will need the unchosen ones in Step 4.

**STEP 2 — Methods** (research techniques):
- List exactly 5 research methods or techniques relevant to their chosen aspects, as a numbered list (1-5).
- Ask the user to pick the ones they use or are interested in.
- After they choose, ask: "Would you like to see more methods, or shall we move on to applications?"
- If they want more, list 5 more methods and repeat. If they want to move on, go to Step 3.

**STEP 3 — Applications** (domains / use cases):
- List exactly 5 application domains or use cases relevant to their topic and chosen aspects, as a numbered list (1-5).
- Ask the user to pick the relevant ones.
- After they choose, ask: "Would you like to see more application areas, or shall we move on to define the scope?"
- If they want more, list 5 more applications and repeat. If they want to move on, go to Step 4.

**STEP 4 — Scope** (exclusions):
- List the sub-topics from Step 1 that the user did NOT choose, plus any other potentially related but out-of-scope areas.
- Present them as a numbered list and ask: "Would you like to explicitly exclude any of these from your research interest?"
- After they respond, say: "Great, I now have a comprehensive picture of your research interest. You can generate the summary now."

**RULES**:
- Always present options as a numbered list (1. ... 2. ... etc.)
- Keep each message concise — list the options, then ask one clear question
- Acknowledge the user's choices briefly before presenting the next list
- Use domain-appropriate academic terminology
- If the user's response is unclear, ask for clarification
- Do NOT skip steps or combine steps
- Do NOT generate a summary yourself — the user will click a button to do that
- When you reach the end of Step 4, include the phrase "generate the summary" so the system knows the conversation is complete

**Tone**: Helpful, professional, and conversational. You're a knowledgeable colleague."""
    
    def _mock_response(
        self,
        user_message: str,
        conversation_history: List[Message],
        topic_text: str
    ) -> str:
        """
        Generate a scripted mock response for local development.
        Simulates the structured 4-step selection flow without calling AWS Bedrock.
        """
        turn = len(conversation_history)  # number of messages so far (before this exchange)

        if turn == 0:
            # Step 1: List 5 aspects
            return (
                f"Great, let's define your research interest in **{topic_text}**. "
                "I'll walk you through a few steps to capture the details.\n\n"
                "**Step 1 — Aspects**: Here are 5 specific sub-topics within this area:\n\n"
                "1. Theoretical foundations and mathematical modeling\n"
                "2. Computational methods and simulation techniques\n"
                "3. Experimental measurement and validation\n"
                "4. Design optimization and parameter tuning\n"
                "5. Standards compliance and industry benchmarks\n\n"
                "Which of these interest you? (e.g., \"1, 3, 5\")"
            )
        elif turn <= 2:
            # Step 1 follow-up: confirm or list more
            return (
                "Good choices! Would you like to explore more sub-topics, "
                "or shall we move on to research methods?"
            )
        elif turn <= 4:
            # Step 2: List 5 methods
            return (
                "**Step 2 — Methods**: Here are 5 research techniques relevant to your interests:\n\n"
                "1. Finite element analysis (FEA)\n"
                "2. Machine learning / deep learning approaches\n"
                "3. Statistical analysis and data mining\n"
                "4. Experimental prototyping and testing\n"
                "5. Analytical / closed-form modeling\n\n"
                "Which methods are you interested in?"
            )
        elif turn <= 6:
            # Step 2 follow-up
            return (
                "Noted! Would you like to see more methods, "
                "or shall we move on to applications?"
            )
        elif turn <= 8:
            # Step 3: List 5 applications
            return (
                "**Step 3 — Applications**: Here are 5 application domains:\n\n"
                "1. Consumer electronics\n"
                "2. Automotive systems\n"
                "3. Aerospace and defense\n"
                "4. Telecommunications\n"
                "5. Biomedical devices\n\n"
                "Which application areas are relevant to your research?"
            )
        elif turn <= 10:
            # Step 3 follow-up
            return (
                "Great selections! Would you like to see more application areas, "
                "or shall we move on to define the scope?"
            )
        elif turn <= 12:
            # Step 4: Scope / exclusions
            return (
                "**Step 4 — Scope**: Based on our conversation, here are some areas "
                "you didn't select that we could explicitly exclude:\n\n"
                "1. Standards compliance and industry benchmarks\n"
                "2. Design optimization and parameter tuning\n"
                "3. Biomedical devices\n"
                "4. Aerospace and defense\n\n"
                "Would you like to explicitly exclude any of these from your research interest?"
            )
        else:
            return (
                "Great, I now have a comprehensive picture of your research interest. "
                "You can generate the summary now."
            )

    def _mock_generate_description(self, conversation_history: List[Message], topic_text: str = "") -> str:
        """Generate a mock comprehensive description for local development."""
        # Extract user messages to build a realistic description
        user_msgs = [m.content for m in conversation_history if m.role == "user" and m.content.strip()]
        context = " ".join(user_msgs[:4]) if user_msgs else topic_text

        return (
            f"Research focused on {topic_text or 'the specified topic'} with emphasis on the specific "
            f"aspects and methodologies discussed. The researcher is interested in exploring: {context[:200]}. "
            "This includes relevant application domains and excludes out-of-scope areas as identified "
            "during the conversation. The research aims to advance understanding through systematic "
            "investigation using appropriate analytical and experimental techniques."
        )

    def send_message(
        self,
        user_message: str,
        conversation_history: List[Message],
        topic_text: str,
        user_id: str = "",
        topic_id: str = ""
    ) -> ChatbotResponse:
        """
        Process user message and generate chatbot response.
        
        Args:
            user_message: User's input message
            conversation_history: Previous messages in conversation
            topic_text: Simple topic text for context
            user_id: User ID for metrics (optional)
            topic_id: Topic ID for metrics (optional)
            
        Returns:
            Chatbot response with message and conversation state
            
        Raises:
            TimeoutError: If response generation exceeds 5 seconds
            AIServiceError: If Bedrock API fails after retries
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.1, 9.1, 9.2
        """
        start_time = time.time()
        metrics = get_metrics_service()
        
        try:
            # --- Mock mode for local development (no AWS credentials needed) ---
            if self.mock_mode:
                response_text = self._mock_response(user_message, conversation_history, topic_text)
                should_conclude = self.should_conclude_conversation(
                    conversation_history + [
                        Message(role="user", content=user_message, timestamp=datetime.utcnow().isoformat()),
                        Message(role="assistant", content=response_text, timestamp=datetime.utcnow().isoformat()),
                    ]
                )
                status = ConversationStatus.COMPLETED if should_conclude else ConversationStatus.IN_PROGRESS
                return ChatbotResponse(
                    message=response_text,
                    shouldConclude=should_conclude,
                    conversationStatus=status.value
                )

            # Build conversation messages for Claude API
            messages = self._build_conversation_messages(
                user_message,
                conversation_history,
                topic_text
            )
            
            # Call AWS Bedrock Claude API with 5-second timeout
            response_text = self._call_bedrock(messages)
            
            # Determine if conversation should conclude
            should_conclude = self.should_conclude_conversation(
                conversation_history + [
                    Message(
                        role="user",
                        content=user_message,
                        timestamp=datetime.utcnow().isoformat()
                    ),
                    Message(
                        role="assistant",
                        content=response_text,
                        timestamp=datetime.utcnow().isoformat()
                    )
                ]
            )
            
            # Determine conversation status
            if should_conclude:
                status = ConversationStatus.COMPLETED
            elif len(conversation_history) == 0:
                status = ConversationStatus.IN_PROGRESS
            else:
                status = ConversationStatus.IN_PROGRESS
            
            # Log successful response
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(json.dumps({
                "event_type": "chatbot_response_success",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "success",
                "conversation_length": len(conversation_history) + 2,
                "should_conclude": should_conclude
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_chatbot_response_time(duration_ms, user_id, topic_id, success=True)
                metrics.emit_chatbot_success(user_id, topic_id)
            except Exception as e:
                logger.warning(f"Failed to emit success metrics: {e}")
            
            return ChatbotResponse(
                message=response_text,
                shouldConclude=should_conclude,
                conversationStatus=status.value
            )
            
        except ReadTimeoutError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(json.dumps({
                "event_type": "chatbot_response_timeout",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "timeout",
                "error_message": "Chatbot response exceeded 5 second timeout"
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_chatbot_response_time(duration_ms, user_id, topic_id, success=False)
                metrics.emit_chatbot_timeout(user_id, topic_id)
                metrics.emit_chatbot_failure(user_id, topic_id, "timeout")
            except Exception as me:
                logger.warning(f"Failed to emit timeout metrics: {me}")
            
            raise TimeoutError("Chatbot response exceeded 5 second timeout") from e
        except ClientError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(json.dumps({
                "event_type": "chatbot_response_failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "failed",
                "error_type": "bedrock_api_error",
                "error_code": error_code
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_chatbot_response_time(duration_ms, user_id, topic_id, success=False)
                metrics.emit_chatbot_failure(user_id, topic_id, "bedrock_api_error")
                metrics.emit_bedrock_api_error(error_code, "ChatbotResponse")
            except Exception as me:
                logger.warning(f"Failed to emit API error metrics: {me}")
            
            raise AIServiceError(f"AWS Bedrock API error: {error_code}") from e
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(json.dumps({
                "event_type": "chatbot_response_failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_chatbot_response_time(duration_ms, user_id, topic_id, success=False)
                metrics.emit_chatbot_failure(user_id, topic_id, "unexpected_error")
            except Exception as me:
                logger.warning(f"Failed to emit error metrics: {me}")
            
            raise AIServiceError(f"Unexpected error in chatbot service: {str(e)}") from e
    
    def _build_conversation_messages(
        self,
        user_message: str,
        conversation_history: List[Message],
        topic_text: str
    ) -> List[Dict[str, str]]:
        """
        Build conversation messages for Claude API.
        Includes conversation history and current user message.
        Claude requires strictly alternating user/assistant roles.
        """
        messages = []

        # Add conversation history, skipping any empty-content messages
        # and ensuring strict user/assistant alternation
        for msg in conversation_history:
            if not msg.content.strip():
                continue  # skip empty messages (e.g. the initial empty trigger)
            # Only add if it alternates correctly
            if messages and messages[-1]["role"] == msg.role:
                continue  # skip duplicate consecutive roles
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Claude requires the first message to be role=user.
        # If history starts with an assistant message (e.g. the greeting saved
        # without the initial empty user trigger), prepend a synthetic user opener.
        if messages and messages[0]["role"] == "assistant":
            opener = f"I want to define my research interest. The topic is: {topic_text}" if topic_text else "Hello, I'd like to define my research interest."
            messages.insert(0, {"role": "user", "content": opener})

        # Determine content for the new user message
        if len(messages) == 0 and topic_text:
            # First real message — include topic context
            content = f"I want to define my research interest. The topic is: {topic_text}"
            if user_message.strip():
                content = user_message
        else:
            content = user_message

        # Only append if it won't create a consecutive user/user pair
        if not content.strip():
            # Empty trigger message — use topic as the opener
            content = f"I want to define my research interest. The topic is: {topic_text}"

        if messages and messages[-1]["role"] == "user":
            # Merge into the last user message rather than creating a duplicate
            messages[-1]["content"] = messages[-1]["content"] + "\n" + content
        else:
            messages.append({"role": "user", "content": content})

        return messages

        return messages
    
    def _call_bedrock(self, messages: List[Dict[str, str]], client=None, max_tokens=500, system_prompt=None) -> str:
        """
        Call AWS Bedrock with Claude model.
        
        Args:
            messages: Conversation messages in Claude API format
            client: Optional Bedrock client override (e.g. longer timeout for generation)
            max_tokens: Max tokens for response (default 500 for chat, higher for generation)
            system_prompt: Optional system prompt override
            
        Returns:
            Response text
        """
        bedrock_client = client or self.bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt or self.system_prompt,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9
        })
        
        response = bedrock_client.invoke_model(
            modelId=self.model_id,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def generate_comprehensive_description(
        self,
        conversation_history: List[Message],
        user_id: str = "",
        topic_id: str = "",
        topic_text: str = ""
    ) -> str:
        """
        Generate comprehensive description from conversation history.
        Analyzes conversation to extract aspects, methodologies, applications, exclusions.
        
        Args:
            conversation_history: Complete conversation messages
            user_id: User ID for metrics (optional)
            topic_id: Topic ID for metrics (optional)
            
        Returns:
            Structured comprehensive description optimized for Relevance_Evaluator
            
        Raises:
            GenerationError: If description generation fails
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 9.3
        """
        start_time = time.time()
        metrics = get_metrics_service()
        
        if not conversation_history:
            logger.error(json.dumps({
                "event_type": "description_generation_failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error_type": "empty_conversation",
                "error_message": "Cannot generate description from empty conversation"
            }))
            raise GenerationError("Cannot generate description from empty conversation")
        
        # Log generation start
        logger.info(json.dumps({
            "event_type": "description_generation_start",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_length": len(conversation_history)
        }))

        # --- Mock mode for local development ---
        if self.mock_mode:
            return self._mock_generate_description(conversation_history)
        
        try:
            # Build conversation transcript for analysis
            transcript = self._build_conversation_transcript(conversation_history)
            
            # Create prompt for description generation with matching hierarchy:
            # - Aspects & Scope = strict (hard filters)
            # - Methods & Applications = preferred (soft boost)
            generation_prompt = f"""Based on the following conversation about a researcher's interests, generate a structured description for matching academic papers.

Conversation transcript:
{transcript}

Generate the description using this EXACT structure with these four labeled sections. Each section has a different matching priority:

**REQUIRED TOPICS** (papers MUST relate to at least one of these):
List all the specific aspects and sub-topics the user selected. These are hard requirements — a paper must touch on at least one of these to be relevant.

**EXCLUDED TOPICS** (papers must NOT be about these):
List all topics the user explicitly excluded or said they are not interested in. These are hard filters — any paper primarily about an excluded topic should be rejected.

**PREFERRED METHODS** (papers using these methods are ranked higher, but not required):
List the research methods and techniques the user selected. These are soft preferences — papers using these methods should be boosted in ranking, but papers using other methods are still acceptable.

**PREFERRED APPLICATIONS** (papers in these domains are ranked higher, but not required):
List the application domains the user selected. These are soft preferences — papers in these domains should be boosted, but papers in other application areas are still acceptable.

Use the exact section headers shown above (REQUIRED TOPICS, EXCLUDED TOPICS, PREFERRED METHODS, PREFERRED APPLICATIONS). Be specific and use the technical terminology from the conversation. Keep each section concise — bullet points are fine.

Structured Description:"""
            
            # Call Bedrock to generate description (use longer-timeout client)
            messages = [{"role": "user", "content": generation_prompt}]
            description = self._call_bedrock(
                messages,
                client=self.bedrock_gen,
                max_tokens=1500,
                system_prompt="You are a research interest summarizer. Generate structured descriptions of research interests with clear matching priorities. Follow the section format exactly as requested."
            )
            
            # Validate description is not empty
            if not description or not description.strip():
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(json.dumps({
                    "event_type": "description_generation_failed",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "duration_ms": duration_ms,
                    "status": "failed",
                    "error_type": "empty_output",
                    "error_message": "Generated description is empty"
                }))
                raise GenerationError("Generated description is empty")
            
            # Validate description length
            if len(description) > 5000:
                # Truncate if too long
                description = description[:5000]
            
            # Log successful generation
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(json.dumps({
                "event_type": "description_generation_complete",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "success",
                "input_length": len(transcript),
                "output_length": len(description)
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_description_generation_success(user_id, topic_id, duration_ms)
            except Exception as e:
                logger.warning(f"Failed to emit description success metrics: {e}")
            
            return description.strip()
            
        except (ReadTimeoutError, ClientError) as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_code = e.response.get('Error', {}).get('Code', 'Unknown') if isinstance(e, ClientError) else 'Timeout'
            logger.error(json.dumps({
                "event_type": "description_generation_failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "failed",
                "error_type": "bedrock_api_error",
                "error_message": str(e)
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_description_generation_failure(user_id, topic_id, "bedrock_api_error")
                if isinstance(e, ClientError):
                    metrics.emit_bedrock_api_error(error_code, "DescriptionGeneration")
            except Exception as me:
                logger.warning(f"Failed to emit description failure metrics: {me}")
            
            raise GenerationError(f"Failed to generate description: {str(e)}") from e
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(json.dumps({
                "event_type": "description_generation_failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "status": "failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }))
            
            # Emit CloudWatch metrics (don't let metrics failures break the response)
            try:
                metrics.emit_description_generation_failure(user_id, topic_id, "unexpected_error")
            except Exception as me:
                logger.warning(f"Failed to emit description error metrics: {me}")
            
            raise GenerationError(f"Unexpected error generating description: {str(e)}") from e
    
    def _build_conversation_transcript(self, conversation_history: List[Message]) -> str:
        """
        Build a readable transcript from conversation history.
        """
        transcript_lines = []
        for msg in conversation_history:
            role_label = "User" if msg.role == "user" else "Assistant"
            transcript_lines.append(f"{role_label}: {msg.content}")
        
        return "\n\n".join(transcript_lines)
    
    def should_conclude_conversation(
        self,
        conversation_history: List[Message]
    ) -> bool:
        """
        Determine if sufficient information has been gathered.
        In the structured flow, the assistant says "generate the summary"
        when all 4 steps are complete. We ONLY check for that explicit phrase
        to avoid false positives from transition questions mentioning future steps.
        
        Args:
            conversation_history: Current conversation messages
            
        Returns:
            True if conversation can conclude, False otherwise
            
        Requirements: 2.7
        """
        if len(conversation_history) < 6:
            return False
        
        # Only trigger when the assistant explicitly says the completion phrase
        assistant_messages = [msg for msg in conversation_history if msg.role == "assistant"]
        if assistant_messages:
            latest = assistant_messages[-1].content.lower()
            if "generate the summary" in latest:
                return True
        
        return False


class AIServiceError(Exception):
    """Exception raised when AI service fails"""
    pass


class GenerationError(Exception):
    """Exception raised when description generation fails"""
    pass
