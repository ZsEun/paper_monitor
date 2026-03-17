from app.scrapers.ieee_scraper import IEEEScraper
from app.scrapers.topic_classifier import TopicClassifier
from app.services.ai_service import AIService
from app.services.relevance_evaluator import RelevanceEvaluator
from app.utils.storage import read_json_file, write_json_file, get_user_interest_topics
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
import logging

logger = logging.getLogger(__name__)


class JournalMonitor:
    """Monitor journals and generate digests"""
    
    def __init__(self):
        self.scraper = IEEEScraper()
        self.classifier = TopicClassifier()
        self.ai_service = AIService()
        self.relevance_evaluator = RelevanceEvaluator()
        self.use_ai = True  # Flag to enable/disable AI features
    
    def monitor_journals(self, skip_summaries: bool = False):
        """
        Check all journals for new papers
        
        Args:
            skip_summaries: If True, skip generating AI summaries (will be done later for relevant papers only)
        """
        print("Starting journal monitoring...")
        
        # Get all journals
        journals = read_json_file("journals.json")
        if not journals:
            print("No journals to monitor")
            return
        
        all_papers = []
        
        # Scrape each journal
        for journal_id, journal in journals.items():
            print(f"Monitoring: {journal['name']}")
            papers = self.scraper.scrape_journal(journal['url'], journal_id)
            
            # Process each paper with AI
            for paper in papers:
                paper['id'] = str(uuid.uuid4())
                
                if self.use_ai:
                    try:
                        # First, validate if this is actually an academic paper
                        print(f"  Validating: {paper['title'][:50]}...")
                        is_valid = self.ai_service.is_academic_paper(
                            paper['title'],
                            paper['abstract']
                        )
                        
                        if not is_valid:
                            print(f"  ❌ Skipping non-paper: {paper['title'][:50]}...")
                            continue
                        
                        print(f"  ✓ Valid paper: {paper['title'][:50]}...")
                        
                        # Extract topics using AI (always needed for relevance evaluation)
                        print(f"  Extracting topics with AI...")
                        paper['topics'] = self.ai_service.extract_topics(
                            paper['title'],
                            paper['abstract']
                        )
                        
                        # Only generate summary if not skipping (optimization for filtered digests)
                        if not skip_summaries:
                            print(f"  Generating AI summary...")
                            paper['aiSummary'] = self.ai_service.generate_summary(
                                paper['title'], 
                                paper['abstract']
                            )
                        else:
                            # Placeholder - will be generated later for relevant papers
                            paper['aiSummary'] = None
                        
                        all_papers.append(paper)
                    except Exception as e:
                        print(f"  AI processing failed: {e}, using fallback")
                        paper['aiSummary'] = paper['abstract'][:200] + "..."
                        paper['topics'] = self.classifier.classify(paper)
                        all_papers.append(paper)
                else:
                    # Fallback to rule-based classification
                    paper['aiSummary'] = paper['abstract']
                    paper['topics'] = self.classifier.classify(paper)
                    all_papers.append(paper)
        
        print(f"Found {len(all_papers)} papers")
        return all_papers
    
    def filter_papers_by_relevance(
        self, 
        papers: List[Dict], 
        interest_topics: List[Dict],
        user_id: str
    ) -> tuple[List[Dict], Dict]:
        """
        Filter papers by relevance to user's interest topics using parallel evaluation.
        Then generate AI summaries only for relevant papers (optimization).
        
        Args:
            papers: List of paper dictionaries
            interest_topics: List of user's interest topic dictionaries (with topicText and optional comprehensiveDescription)
            user_id: User ID for logging
            
        Returns:
            Tuple of (relevant_papers, evaluation_metadata, paper_matches)
        """
        if not interest_topics:
            # No filtering if no interest topics
            return papers, {
                'totalPapersEvaluated': 0,
                'relevantPapersIncluded': len(papers),
                'evaluationErrors': 0,
                'hadInterestTopics': False
            }, None
        
        print(f"Filtering {len(papers)} papers by relevance to {len(interest_topics)} topics...")
        
        relevant_papers = []
        paper_matches = []
        evaluation_errors = 0
        
        # Use ThreadPoolExecutor for parallel evaluation (max 10 concurrent)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all evaluation tasks
            future_to_paper = {
                executor.submit(
                    self._evaluate_paper_relevance,
                    paper,
                    interest_topics,
                    user_id
                ): paper
                for paper in papers
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    result = future.result()
                    
                    if result['error']:
                        evaluation_errors += 1
                        logger.warning(f"Evaluation error for paper {paper['id']}: {result['error']}")
                    
                    if result['is_relevant']:
                        relevant_papers.append(paper)
                        paper_matches.append({
                            'paperId': paper['id'],
                            'matchingTopics': result['matching_topics']
                        })
                        print(f"  ✓ Relevant: {paper['title'][:60]}... (matches: {result['matching_topics']})")
                    else:
                        print(f"  ✗ Not relevant: {paper['title'][:60]}...")
                        
                except Exception as e:
                    evaluation_errors += 1
                    logger.error(f"Failed to evaluate paper {paper['id']}: {e}")
        
        # OPTIMIZATION: Generate AI summaries only for relevant papers
        if relevant_papers and self.use_ai:
            print(f"\nGenerating AI summaries for {len(relevant_papers)} relevant papers...")
            for idx, paper in enumerate(relevant_papers):
                if paper.get('aiSummary') is None:  # Only if not already generated
                    try:
                        print(f"  [{idx+1}/{len(relevant_papers)}] Summarizing: {paper['title'][:60]}...")
                        paper['aiSummary'] = self.ai_service.generate_summary(
                            paper['title'],
                            paper['abstract']
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate summary for paper {paper['id']}: {e}")
                        paper['aiSummary'] = paper['abstract'][:200] + "..."
        
        evaluation_metadata = {
            'totalPapersEvaluated': len(papers),
            'relevantPapersIncluded': len(relevant_papers),
            'evaluationErrors': evaluation_errors,
            'hadInterestTopics': True
        }
        
        print(f"Filtered to {len(relevant_papers)} relevant papers ({evaluation_errors} errors)")
        
        return relevant_papers, evaluation_metadata, paper_matches
    
    def _evaluate_paper_relevance(
        self,
        paper: Dict,
        interest_topics: List[Dict],
        user_id: str
    ) -> Dict:
        """
        Evaluate a single paper's relevance.
        
        Args:
            paper: Paper dictionary
            interest_topics: List of interest topic dictionaries (with topicText and optional comprehensiveDescription)
            user_id: User ID for logging
            
        Returns:
            Dictionary with is_relevant, matching_topics, and error fields
        """
        try:
            # Add user_id to paper for logging
            paper_with_user = {**paper, 'user_id': user_id}
            
            # Evaluate relevance
            result = self.relevance_evaluator.evaluate(paper_with_user, interest_topics)
            
            return {
                'is_relevant': result.is_relevant,
                'matching_topics': result.matching_topics,
                'confidence': result.confidence,
                'error': result.error
            }
        except Exception as e:
            logger.error(f"Error evaluating paper {paper.get('id', 'unknown')}: {e}")
            return {
                'is_relevant': False,
                'matching_topics': [],
                'confidence': 0.0,
                'error': str(e)
            }
    
    def generate_digest(self, user_id: Optional[str] = None):
        """
        Generate a weekly digest with optional relevance filtering.
        
        Args:
            user_id: Optional user ID for personalized filtering
        """
        print("Generating weekly digest...")
        
        # Check if user has interest topics to determine if we should skip summaries initially
        skip_summaries = False
        if user_id:
            try:
                interest_topics_data = get_user_interest_topics(user_id)
                interest_topics = [topic['topicText'] for topic in interest_topics_data]
                if interest_topics:
                    skip_summaries = True  # Optimization: skip summaries, generate only for relevant papers
                    print(f"User has {len(interest_topics)} interest topics - will generate summaries only for relevant papers")
            except Exception as e:
                logger.warning(f"Could not check interest topics: {e}")
        
        # Monitor journals to get papers (skip summaries if we'll filter)
        papers = self.monitor_journals(skip_summaries=skip_summaries)
        
        if not papers:
            print("No papers found")
            return None
        
        # Check if user has interest topics for filtering
        evaluation_metadata = None
        paper_matches = None
        
        if user_id:
            try:
                # Get user's interest topics (full objects with comprehensiveDescription)
                interest_topics_data = get_user_interest_topics(user_id)
                
                if interest_topics_data:
                    print(f"User has {len(interest_topics_data)} interest topics - applying relevance filtering")
                    
                    # Filter papers by relevance (summaries generated inside for relevant papers only)
                    papers, evaluation_metadata, paper_matches = self.filter_papers_by_relevance(
                        papers,
                        interest_topics_data,
                        user_id
                    )
                    
                    if not papers:
                        print("No relevant papers found after filtering")
                        # Still create digest but with empty papers
                else:
                    print("User has no interest topics - including all papers")
                    # Generate summaries for all papers since we skipped them earlier
                    if skip_summaries and self.use_ai:
                        print(f"Generating AI summaries for all {len(papers)} papers...")
                        for idx, paper in enumerate(papers):
                            if paper.get('aiSummary') is None:
                                try:
                                    print(f"  [{idx+1}/{len(papers)}] Summarizing: {paper['title'][:60]}...")
                                    paper['aiSummary'] = self.ai_service.generate_summary(
                                        paper['title'],
                                        paper['abstract']
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to generate summary: {e}")
                                    paper['aiSummary'] = paper['abstract'][:200] + "..."
                    
                    evaluation_metadata = {
                        'totalPapersEvaluated': 0,
                        'relevantPapersIncluded': len(papers),
                        'evaluationErrors': 0,
                        'hadInterestTopics': False
                    }
            except Exception as e:
                logger.error(f"Error during relevance filtering: {e}")
                print(f"Relevance filtering failed: {e} - falling back to unfiltered digest")
                
                # Generate summaries if we skipped them earlier
                if skip_summaries and self.use_ai:
                    print(f"Generating AI summaries for all {len(papers)} papers (fallback)...")
                    for idx, paper in enumerate(papers):
                        if paper.get('aiSummary') is None:
                            try:
                                paper['aiSummary'] = self.ai_service.generate_summary(
                                    paper['title'],
                                    paper['abstract']
                                )
                            except Exception as e2:
                                logger.error(f"Failed to generate summary: {e2}")
                                paper['aiSummary'] = paper['abstract'][:200] + "..."
                
                # Graceful degradation - include all papers
                evaluation_metadata = {
                    'totalPapersEvaluated': len(papers),
                    'relevantPapersIncluded': len(papers),
                    'evaluationErrors': 1,
                    'hadInterestTopics': True,
                    'filteringError': str(e)
                }
        
        # Group papers by topic
        papers_by_topic = {}
        topic_groups = []
        
        for paper in papers:
            for topic in paper['topics']:
                if topic not in papers_by_topic:
                    papers_by_topic[topic] = []
                papers_by_topic[topic].append(paper)
        
        # Create topic groups
        for topic, topic_papers in papers_by_topic.items():
            topic_groups.append({
                'topic': topic,
                'paperCount': len(topic_papers),
                'papers': topic_papers
            })
        
        # Create digest
        digest_id = str(uuid.uuid4())
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        digest = {
            'id': digest_id,
            'generatedAt': today.isoformat(),
            'startDate': week_ago.strftime('%Y-%m-%d'),
            'endDate': today.strftime('%Y-%m-%d'),
            'papers': papers,
            'papersByTopic': papers_by_topic,
            'topicGroups': topic_groups
        }
        
        # Add evaluation metadata if filtering was applied
        if evaluation_metadata:
            digest['evaluationMetadata'] = evaluation_metadata
        if paper_matches:
            digest['paperMatches'] = paper_matches
        
        # Save digest
        digests = read_json_file("digests.json")
        digests[digest_id] = digest
        write_json_file("digests.json", digests)
        
        print(f"Digest generated: {digest_id}")
        return digest
