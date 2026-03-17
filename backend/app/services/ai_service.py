import boto3
import json
from typing import List, Dict
import os

class AIService:
    """AI service using AWS Bedrock for summarization and topic extraction"""
    
    def __init__(self):
        # Initialize Bedrock client
        # Will automatically use AWS credentials from environment/CLI
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'  # Your configured region
        )
        
        # Use Claude 3 Sonnet model
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    def generate_summary(self, title: str, abstract: str) -> str:
        """
        Generate a structured summary from paper title and abstract
        Format: Problem, Idea, Result (each on separate line)
        """
        prompt = f"""Analyze this research paper and create a structured summary. Fill in each section with actual content from the paper - do NOT leave any brackets or placeholders.

Format:

Problem: [Write one line describing the problem being addressed]

Idea: [Write one line describing the key approach or method]

Result: [Write one line describing the main outcome, contribution, or achievement]

Important: Replace ALL bracketed text with actual content. Do not include any [] brackets in your response.

Title: {title}

Abstract: {abstract}

Structured Summary:"""
        
        try:
            response = self._call_bedrock(prompt, max_tokens=250)
            # Remove any remaining brackets as a safety measure
            cleaned = response.strip().replace('[', '').replace(']', '')
            return cleaned
        except Exception as e:
            print(f"Error generating summary: {e}")
            # Fallback to truncated abstract
            return f"Problem: See abstract\n\nIdea: {abstract[:100]}...\n\nResult: See full paper"
    
    def extract_topics(self, title: str, abstract: str) -> List[str]:
        """
        Extract relevant research topics from paper title and abstract
        """
        prompt = f"""Analyze this research paper and identify the main research topics/areas it belongs to. 
Choose from these categories: Machine Learning, EMC, Signal Processing, RF, Circuit Design, Power Electronics, Antenna Design, Wireless Communication, IoT, Sensors, Other.

Return ONLY a comma-separated list of 1-3 most relevant topics, nothing else.

Title: {title}

Abstract: {abstract}

Topics:"""
        
        try:
            response = self._call_bedrock(prompt, max_tokens=50)
            # Parse comma-separated topics
            topics = [t.strip() for t in response.split(',') if t.strip()]
            return topics[:3] if topics else ['Other']
        except Exception as e:
            print(f"Error extracting topics: {e}")
            return ['Other']
    
    def is_academic_paper(self, title: str, abstract: str) -> bool:
        """
        Determine if the content is an actual academic paper or not.
        Returns True if it's a research paper, False if it's metadata/TOC/publication info.
        Uses simple rule-based validation for reliability.
        """
        # Use simple rule-based validation only
        # AI validation is too aggressive when abstracts are missing
        return self._simple_paper_validation(title, abstract)
    
    def _simple_paper_validation(self, title: str, abstract: str) -> bool:
        """
        Simple rule-based validation as fallback
        """
        title_lower = title.lower()
        abstract_lower = abstract.lower()
        
        # Keywords that indicate non-paper content
        non_paper_keywords = [
            'table of contents',
            'publication information',
            'front cover',
            'back cover',
            'editorial',
            'index',
            'announcement',
            'society information',
            'front matter',
            'back matter',
            'blank page',
            'share your preprint',
            'information for authors',
            'author guidelines',
            'submission guidelines',
            'call for papers',
            'instructions for authors'
        ]
        
        for keyword in non_paper_keywords:
            if keyword in title_lower:
                return False
        
        # If title is very short (less than 20 chars), likely not a real paper
        if len(title) < 20:
            return False
        
        # If abstract is missing, still accept if title looks like a paper
        # (many IEEE papers don't have abstracts in the listing page)
        return True
    
    def _call_bedrock(self, prompt: str, max_tokens: int = 200) -> str:
        """
        Call AWS Bedrock with Claude model
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "top_p": 0.9
        })
        
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
