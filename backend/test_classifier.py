#!/usr/bin/env python3
"""Test the topic classifier"""

from app.scrapers.topic_classifier import TopicClassifier

# Create classifier
classifier = TopicClassifier()

# Test papers
test_papers = [
    {
        'title': 'Deep Learning for Signal Processing Applications',
        'abstract': 'We propose a novel neural network architecture for processing signals in real-time applications.'
    },
    {
        'title': 'EMC Analysis of High-Speed PCB Designs',
        'abstract': 'This paper presents electromagnetic compatibility analysis techniques for printed circuit boards with focus on interference reduction.'
    },
    {
        'title': 'Machine Learning Based Antenna Design',
        'abstract': 'We use artificial intelligence and deep learning to optimize RF antenna parameters for wireless communication systems.'
    },
    {
        'title': 'Power Converter Design for Electric Vehicles',
        'abstract': 'A new inverter topology is proposed for high-efficiency power electronics in automotive applications.'
    },
]

# Test each paper
print("=" * 80)
print("TOPIC CLASSIFIER TEST")
print("=" * 80)

for i, paper in enumerate(test_papers, 1):
    print(f"\n📄 Paper {i}:")
    print(f"Title: {paper['title']}")
    print(f"Abstract: {paper['abstract'][:80]}...")
    
    topics = classifier.classify(paper)
    print(f"✓ Detected Topics: {', '.join(topics)}")
    print("-" * 80)

print("\n✅ Test complete!")
