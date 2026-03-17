from typing import List, Dict

class TopicClassifier:
    """Classify papers into topics based on keywords"""
    
    def __init__(self):
        # Define topic keywords
        self.topic_keywords = {
            'Machine Learning': ['machine learning', 'deep learning', 'neural network', 'ai', 'artificial intelligence'],
            'Signal Processing': ['signal processing', 'dsp', 'filter', 'fourier'],
            'EMC': ['emc', 'electromagnetic compatibility', 'emi', 'interference'],
            'Power Electronics': ['power', 'converter', 'inverter', 'rectifier'],
            'RF': ['rf', 'radio frequency', 'antenna', 'wireless'],
            'Circuit Design': ['circuit', 'analog', 'digital', 'vlsi', 'ic design'],
        }
    
    def classify(self, paper: Dict) -> List[str]:
        """
        Classify a paper into topics based on title and abstract
        Returns list of matching topics
        """
        topics = []
        text = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
        
        # If no topics matched, assign to "Other"
        if not topics:
            topics.append('Other')
        
        return topics
