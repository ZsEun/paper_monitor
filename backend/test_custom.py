#!/usr/bin/env python3
"""Test classifier with your own paper"""

from app.scrapers.topic_classifier import TopicClassifier

classifier = TopicClassifier()

# Add your own paper here
my_paper = {
    'title': 'YOUR PAPER TITLE HERE',
    'abstract': 'YOUR PAPER ABSTRACT HERE'
}

print("Testing your paper:")
print(f"Title: {my_paper['title']}")
print(f"Abstract: {my_paper['abstract']}")
print()

topics = classifier.classify(my_paper)
print(f"Detected Topics: {', '.join(topics)}")
