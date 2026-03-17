#!/usr/bin/env python3
"""
Quick relevance testing script.
Tests a paper against your saved interest topics using the real RelevanceEvaluator.

Usage:
  # Interactive mode
  python test_relevance_quick.py

  # CLI mode (for automation)
  python test_relevance_quick.py --title "Paper Title" --abstract "Paper abstract text"
"""
import sys
import os
import json
import argparse

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.services.relevance_evaluator import RelevanceEvaluator
from app.utils.storage import read_json_file


def load_user_topics():
    """Load all interest topics from storage"""
    data = read_json_file("interest_topics.json")
    topics = data.get("topics", [])
    if not topics:
        print("ERROR: No interest topics found in data/interest_topics.json")
        sys.exit(1)
    return topics


def evaluate_paper(evaluator, topics, title, abstract):
    """Run evaluation and print results"""
    paper = {
        "id": "test-paper",
        "title": title,
        "abstract": abstract,
        "keywords": []
    }

    result = evaluator.evaluate(paper, topics)

    print(f"\nTitle:      {title[:100]}")
    print(f"Relevant:   {'YES' if result.is_relevant else 'NO'}")
    print(f"Confidence: {result.confidence}")
    print(f"Matching:   {result.matching_topics}")
    if result.error:
        print(f"Error:      {result.error}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Test paper relevance")
    parser.add_argument("--title", "-t", help="Paper title")
    parser.add_argument("--abstract", "-a", help="Paper abstract")
    args = parser.parse_args()

    topics = load_user_topics()
    evaluator = RelevanceEvaluator()

    print(f"Loaded {len(topics)} interest topic(s)")
    for t in topics:
        has_desc = "structured" if t.get("comprehensiveDescription") else "plain"
        print(f"  - {t.get('topicText', '?')} ({has_desc})")

    if args.title:
        # CLI mode
        evaluate_paper(evaluator, topics, args.title, args.abstract or "")
    else:
        # Interactive mode
        print("\nPaste title, then abstract. Blank line to evaluate. 'quit' to exit.\n")
        while True:
            title = input("Title (or 'quit'): ").strip()
            if title.lower() == "quit":
                break
            print("Abstract (blank line to finish):")
            lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
            abstract = " ".join(lines).strip() or "No abstract."
            evaluate_paper(evaluator, topics, title, abstract)
            print()


if __name__ == "__main__":
    main()
