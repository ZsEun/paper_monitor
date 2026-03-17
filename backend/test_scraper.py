#!/usr/bin/env python3
"""Test script to debug IEEE scraper"""

from app.scrapers.ieee_scraper import IEEEScraper
from app.scrapers.topic_classifier import TopicClassifier
import json

def test_scraper():
    scraper = IEEEScraper()
    classifier = TopicClassifier()
    
    # Test with TEMC journal
    journal_url = "https://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=15"
    journal_id = "test-journal"
    
    print(f"Testing scraper with: {journal_url}\n")
    
    papers = scraper.scrape_journal(journal_url, journal_id)
    
    print(f"\n{'='*80}")
    print(f"Found {len(papers)} papers")
    print(f"{'='*80}\n")
    
    for i, paper in enumerate(papers, 1):
        print(f"\nPaper {i}:")
        print(f"  Title: {paper['title']}")
        print(f"  Authors: {', '.join(paper['authors'])}")
        print(f"  Abstract: {paper['abstract'][:100]}...")
        print(f"  URL: {paper['url']}")
        print(f"  Published: {paper['publishedDate']}")
        
        # Classify the paper
        topics = classifier.classify(paper)
        print(f"  Topics: {', '.join(topics)}")

if __name__ == "__main__":
    test_scraper()
