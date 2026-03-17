"""
RelevanceEvaluator service for determining paper relevance to user interest topics.

Uses AWS Bedrock Claude to evaluate if a paper matches user's research interests.
"""
import boto3
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RelevanceResult:
    """Result of relevance evaluation"""
    is_relevant: bool
    matching_topics: List[str]
    confidence: float
    error: Optional[str] = None


class RelevanceEvaluator:
    """
    Evaluates paper relevance to user interest topics using AWS Bedrock Claude.
    """
    
    def __init__(self):
        """Initialize the RelevanceEvaluator with Bedrock client"""
        from botocore.config import Config
        
        # Initialize Bedrock client with reasonable timeout for evaluation
        bedrock_config = Config(
            read_timeout=30,
            retries={'max_attempts': 2}
        )
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2',
            config=bedrock_config
        )
        
        # Use Claude 3 Sonnet model
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        
        # Load prompt templates
        self.prompt_template = self._get_default_prompt_template()
    
    def evaluate(self, paper: Dict, interest_topics: List[Dict]) -> RelevanceResult:
        """
        Evaluate if a paper is relevant to user's interest topics.
        
        Args:
            paper: Dictionary with paper metadata (title, abstract, keywords, etc.)
            interest_topics: List of interest topic dictionaries with topicText and optional comprehensiveDescription
            
        Returns:
            RelevanceResult with is_relevant, matching_topics, and confidence
        """
        if not interest_topics:
            # No interest topics - paper is not relevant by default
            return RelevanceResult(
                is_relevant=False,
                matching_topics=[],
                confidence=1.0
            )
        
        try:
            # Extract descriptions from topics (use comprehensiveDescription if available, else topicText)
            topic_descriptions = []
            for topic in interest_topics:
                if isinstance(topic, dict):
                    # Use comprehensiveDescription if available and not empty
                    desc = topic.get('comprehensiveDescription')
                    if desc and desc.strip():
                        topic_descriptions.append(desc)
                    else:
                        # Fall back to topicText
                        topic_descriptions.append(topic.get('topicText', ''))
                else:
                    # Legacy support: if topic is a string, use it directly
                    topic_descriptions.append(str(topic))
            
            # Construct prompt with paper and topic descriptions
            prompt = self._construct_prompt(paper, topic_descriptions)
            
            # Call Bedrock with timeout
            response_text = self._call_bedrock(prompt, timeout=5)
            
            # Parse response
            result = self._parse_response(response_text)
            
            # Log decision for audit
            self._log_decision(paper, topic_descriptions, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating paper {paper.get('id', 'unknown')}: {e}")
            # Return not relevant on error (graceful degradation)
            return RelevanceResult(
                is_relevant=False,
                matching_topics=[],
                confidence=0.0,
                error=str(e)
            )
    
    def _construct_prompt(self, paper: Dict, interest_topics: List[str]) -> str:
        """
        Construct evaluation prompt from paper and interest topics.
        Detects structured descriptions (with REQUIRED TOPICS / EXCLUDED TOPICS / etc.)
        and uses the structured prompt template. Falls back to legacy template for plain text.
        
        Args:
            paper: Paper metadata dictionary
            interest_topics: List of interest topic strings (may contain structured descriptions)
            
        Returns:
            Formatted prompt string
        """
        title = paper.get('title', 'No title')
        abstract = paper.get('abstract', 'No abstract available')
        keywords = paper.get('keywords', [])
        
        # Format keywords
        keywords_str = ', '.join(keywords) if keywords else 'None provided'
        
        # Check if any topic description uses the structured format
        combined_description = '\n\n'.join(interest_topics)
        is_structured = ('REQUIRED TOPICS' in combined_description or 
                         'EXCLUDED TOPICS' in combined_description or
                         'PREFERRED METHODS' in combined_description or
                         'PREFERRED APPLICATIONS' in combined_description)
        
        if is_structured:
            # Use structured prompt that understands the matching hierarchy
            prompt = self._get_structured_prompt_template().format(
                title=title,
                abstract=abstract,
                keywords=keywords_str,
                interest_description=combined_description
            )
        else:
            # Legacy: flat topic list
            topics_str = '\n'.join(f"- {topic}" for topic in interest_topics)
            prompt = self.prompt_template.format(
                title=title,
                abstract=abstract,
                keywords=keywords_str,
                interest_topics=topics_str
            )
        
        return prompt
    
    def _call_bedrock(self, prompt: str, timeout: int = 5) -> str:
        """
        Call AWS Bedrock with Claude model.
        
        Args:
            prompt: The prompt to send
            timeout: Timeout in seconds (not directly supported by boto3, logged for monitoring)
            
        Returns:
            Response text from Claude
            
        Raises:
            Exception: On API errors or timeouts
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "system": "You are a strict research paper classifier. FIRST identify the paper's primary device/system type — the core thing being designed or analyzed. Then check if that SAME device/system type appears in the user's interest topics. Qualifiers like 'wideband', 'multi-band', 'compact', 'tunable' describe properties, NOT device types. Two DIFFERENT device types sharing a property (e.g., both are 'multi-band') are NOT the same topic. A paper about device-type A is only relevant to a topic about device-type B if A and B are the same kind of thing. CRITICAL: Once you identify the primary subject, you MUST commit to it. If the primary subject is X, and X is not the same device type as the interest topic, the answer is NOT relevant — even if the interest topic's device appears as a sub-component in the paper. Do NOT let secondary mentions override the primary subject. COMPOUND TOPICS: When a required topic specifies BOTH a method and a device (e.g., 'Machine learning for antenna optimization'), the paper MUST use that specific method on that specific device. A paper about the device that does NOT use the specified method does NOT match. Hardware control techniques, communication protocols, and signal processing are NOT the same as machine learning.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.0,  # Zero temperature for maximum consistency
            "top_p": 0.9
        })
        
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise
    
    def _parse_response(self, response_text: str) -> RelevanceResult:
        """
        Parse Claude's response into RelevanceResult.
        
        Args:
            response_text: Raw response from Claude
            
        Returns:
            RelevanceResult object
            
        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to parse as JSON
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            data = json.loads(response_text)
            
            # Validate required fields
            if 'isRelevant' not in data:
                raise ValueError("Missing 'isRelevant' field in response")
            if 'matchingTopics' not in data:
                raise ValueError("Missing 'matchingTopics' field in response")
            
            is_relevant = bool(data['isRelevant'])
            matching_topics = data['matchingTopics']
            confidence = float(data.get('confidence', 0.8))
            
            # Validate matching_topics is a list
            if not isinstance(matching_topics, list):
                matching_topics = []
            
            # Include preferred matches in matching_topics for downstream reporting
            matching_preferred = data.get('matchingPreferred', [])
            if isinstance(matching_preferred, list) and matching_preferred:
                matching_topics = matching_topics + [f"(preferred) {p}" for p in matching_preferred]
            
            # Log exclusion reason if present
            excluded_hit = data.get('excludedTopicHit')
            if excluded_hit:
                logger.info(f"Paper rejected due to excluded topic: {excluded_hit}")
            
            # Log primary subject for debugging relevance decisions
            primary_subject = data.get('paperPrimarySubject')
            paper_device = data.get('paperDeviceType')
            device_match = data.get('deviceTypeMatch')
            if primary_subject:
                logger.info(f"Paper primary subject: {primary_subject}")
            if paper_device:
                logger.info(f"Paper device type: {paper_device} | Device type match: {device_match}")
            
            return RelevanceResult(
                is_relevant=is_relevant,
                matching_topics=matching_topics,
                confidence=confidence
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text (truncated): {response_text[:200]}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            raise ValueError(f"Failed to parse response: {e}")
    
    def _log_decision(self, paper: Dict, topic_descriptions: List[str], result: RelevanceResult):
        """
        Log evaluation decision for audit trail.
        
        Args:
            paper: Paper metadata
            topic_descriptions: User's interest topic descriptions
            result: Evaluation result
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'paper_id': paper.get('id', 'unknown'),
            'paper_title': paper.get('title', 'unknown'),
            'user_id': paper.get('user_id', 'unknown'),
            'topic_descriptions_count': len(topic_descriptions),
            'is_relevant': result.is_relevant,
            'matching_topics': result.matching_topics,
            'confidence': result.confidence,
            'error': result.error
        }
        
        # Log as structured JSON
        logger.info(f"Relevance evaluation: {json.dumps(log_entry)}")
    
    def _get_default_prompt_template(self) -> str:
        """
        Get the default prompt template for relevance evaluation.
        
        Returns:
            Prompt template string with placeholders
        """
        return """You are an expert research paper evaluator. Your task is to determine if a research paper is relevant to a user's research interests.

Paper Information:
Title: {title}
Abstract: {abstract}
Keywords: {keywords}

User's Research Interest Topics:
{interest_topics}

Instructions:
1. Analyze the paper's title, abstract, and keywords
2. Identify the PRIMARY subject matter and main contribution of the paper — what is this paper fundamentally ABOUT?
3. Determine if the paper's PRIMARY subject matter matches ANY of the user's interest topics
4. Mark as relevant ONLY if the paper is fundamentally about the interest topic, not just sharing some keywords
5. Provide a confidence score (0.0 to 1.0)

Respond ONLY with a JSON object in this exact format:
{{
  "isRelevant": true or false,
  "matchingTopics": ["topic1", "topic2"],
  "confidence": 0.85
}}

CRITICAL Rules for Subject-Matter Matching:
- FIRST identify the paper's primary subject: what TYPE OF DEVICE or SYSTEM is being designed/analyzed/proposed? This is the paper's MAIN CONTRIBUTION.
- Then check: is that SAME TYPE OF DEVICE or SYSTEM listed in the user's interest topics?
- If the paper designs device-type A and the interest topic is about device-type B, they do NOT match — even if A and B share qualifiers like "wideband", "multi-band", "compact", "tunable", etc.
- Qualifiers describe PROPERTIES of a device. Two devices sharing a property does NOT make them the same type of device.
- A component or subsystem that could be USED INSIDE a larger system is NOT the same as that larger system.
- The paper must DESIGN, ANALYZE, or PROPOSE the actual device/system named in the interest topic — not a different device that happens to share some properties.
- COMPOUND TOPIC RULE: If an interest topic specifies both a METHOD and a DEVICE (e.g., "Machine learning techniques for antenna optimization"), the paper must involve BOTH the method AND the device. A paper about the device without the method, or the method without the device, does NOT match.
- IMPORTANT: Once you identify the primary subject, COMMIT to it. If the primary subject is NOT the same type as the interest topic, the paper is NOT relevant — even if the paper uses or incorporates the interest topic's device as a secondary element. A paper whose main contribution is device-type A does not become a paper about device-type B just because B appears as a building block or sub-component.
- isRelevant should be true ONLY if the paper's primary device/system type matches the interest topic's primary device/system type.
- If a paper only mentions a topic in passing or uses it as a sub-component without it being the main contribution, do NOT match it.
- matchingTopics should list the user's topics that match (use exact topic names from the list).
- confidence should be between 0.0 and 1.0.
- Consider synonyms and related concepts within the SAME device/system category.

JSON Response:"""
    
    def _get_structured_prompt_template(self) -> str:
        """
        Get the structured prompt template that understands the matching hierarchy:
        - REQUIRED TOPICS: hard filter (paper must match at least one)
        - EXCLUDED TOPICS: hard rejection (paper must NOT be about these)
        - PREFERRED METHODS: soft boost (rank higher but not required)
        - PREFERRED APPLICATIONS: soft boost (rank higher but not required)
        
        Returns:
            Prompt template string with placeholders
        """
        return """You are an expert research paper evaluator. Your task is to determine if a research paper is relevant to a user's research interests using a structured matching hierarchy.

Paper Information:
Title: {title}
Abstract: {abstract}
Keywords: {keywords}

User's Research Interest Profile:
{interest_description}

FIRST — Identify the paper's PRIMARY SUBJECT:
Before evaluating against the interest profile, determine: What is this paper fundamentally ABOUT?
For example: "This paper is about frequency selective surface (FSS) design" or "This paper is about wideband antenna design."
The primary subject is the THING being designed/analyzed/proposed — not its properties or qualifiers.

Evaluation Rules (STRICT ORDER OF PRIORITY):

1. EXCLUSION CHECK (hard filter — check FIRST):
   - If the paper's PRIMARY subject is an EXCLUDED TOPIC, mark as NOT relevant immediately.
   - A passing mention of an excluded topic is OK; only reject if it's the paper's main subject.

2. REQUIRED TOPICS CHECK (hard filter — STRICT SUBJECT-MATTER MATCHING):
   - The paper's PRIMARY DEVICE/SYSTEM TYPE must match at least one REQUIRED TOPIC's device/system type.
   - Match on DEVICE/SYSTEM TYPE, NOT on shared qualifiers or adjectives.
   - CRITICAL: Qualifiers like "wideband", "multi-band", "compact", "tunable", "reconfigurable" describe PROPERTIES, not device types. Two different device types sharing a property are still different topics.
   - Ask yourself: "Is the paper designing/analyzing the SAME KIND OF THING as the required topic?" If the answer is no, it does not match.
   - A component or subsystem used inside a larger system is NOT the same as that larger system.
   - The paper must DESIGN, ANALYZE, or PROPOSE the actual device/system named in the required topic.
   - IMPORTANT: Once you identify the primary subject, COMMIT to it. If the primary subject is device-type A and the required topic is about device-type B, the paper does NOT match — even if device-type B appears as a sub-component or building block within the paper. The main contribution must BE the required topic's device type.
   - COMPOUND TOPIC RULE: If a required topic specifies both a METHOD and a DEVICE (e.g., "Machine learning techniques for antenna optimization"), the paper must involve BOTH the method AND the device. A paper about the device without the method, or the method without the device, does NOT match.
   - If the paper does not match ANY required topic by device/system type, mark as NOT relevant.

3. PREFERRED METHODS & APPLICATIONS (soft boost — affects confidence only):
   - If the paper also uses a PREFERRED METHOD or targets a PREFERRED APPLICATION, increase the confidence score.
   - These are NOT required for relevance — a paper matching required topics but using different methods is still relevant.
   - Boost confidence by ~0.1 for each preferred match (methods or applications).

Confidence Scoring Guide:
- 0.5-0.6: Matches a required topic but no preferred methods/applications
- 0.7-0.8: Matches a required topic AND one preferred method or application
- 0.85-0.95: Matches a required topic AND both preferred methods and applications
- Reduce confidence by 0.1 if the match is to a secondary (not primary) focus of the paper

Respond ONLY with a JSON object in this exact format:
{{
  "paperPrimarySubject": "brief description of what the paper is fundamentally about",
  "paperDeviceType": "the single core device/system type (1-3 words, e.g. 'antenna', 'metasurface', 'filter', 'frequency selective surface')",
  "requiredTopicDeviceTypes": ["device type from required topic 1", "device type from required topic 2"],
  "deviceTypeMatch": true or false,
  "isRelevant": true or false,
  "matchingTopics": ["matched required topic 1", "matched required topic 2"],
  "matchingPreferred": ["matched preferred method or application"],
  "excludedTopicHit": null or "the excluded topic that caused rejection",
  "confidence": 0.85
}}

FIELD RULES:
- paperDeviceType: Extract ONLY the core device/system type from the paper. Strip all qualifiers. E.g., "wideband filtering transmissive metasurface" → "metasurface". "multi-band antenna array" → "antenna array".
- requiredTopicDeviceTypes: Extract the core device/system type from each required topic. E.g., "Wideband and multi-band antenna design" → "antenna".
- deviceTypeMatch: Is paperDeviceType the same kind of thing as ANY entry in requiredTopicDeviceTypes? This must be a strict type comparison.
- isRelevant: MUST be false if deviceTypeMatch is false. Can also be false if excludedTopicHit is set.

Additional Rules:
- Consider synonyms and related concepts WITHIN the same subject domain
- matchingTopics should list ONLY the required topics that match by subject matter
- matchingPreferred should list any preferred methods/applications that match
- If rejected due to exclusion, set excludedTopicHit to the matching excluded topic

JSON Response:"""

    def load_prompt_template(self, template_key: str = 'relevance_evaluation') -> str:
        """
        Load a prompt template from configuration file.
        
        Args:
            template_key: Key identifying the template (default: 'relevance_evaluation')
            
        Returns:
            Prompt template string
        """
        try:
            import os
            template_file = os.path.join('data', 'prompt_templates.json')
            
            if os.path.exists(template_file):
                with open(template_file, 'r') as f:
                    templates = json.load(f)
                    
                if template_key in templates:
                    return templates[template_key]['template']
            
            # Fallback to default if file doesn't exist or key not found
            logger.warning(f"Template '{template_key}' not found, using default")
            return self._get_default_prompt_template()
            
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return self._get_default_prompt_template()
