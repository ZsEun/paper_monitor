import { User, Journal, Paper, Digest, Credential, TopicGroup } from '../types';

export const mockUser: User = {
  id: '1',
  email: 'user@example.com',
  name: 'John Doe',
};

export const mockJournals: Journal[] = [
  {
    id: '1',
    name: 'IEEE Transactions on Electromagnetic Compatibility',
    platform: 'IEEE Xplore',
    url: 'https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=15',
    addedAt: '2024-01-15',
    isSubscribed: true,
  },
  {
    id: '2',
    name: 'Nature Electronics',
    platform: 'Nature',
    url: 'https://www.nature.com/natelectron/',
    addedAt: '2024-01-20',
    isSubscribed: true,
  },
  {
    id: '3',
    name: 'ACM Computing Surveys',
    platform: 'ACM Digital Library',
    url: 'https://dl.acm.org/journal/csur',
    addedAt: '2024-02-01',
    isSubscribed: false,
  },
];

export const mockPapers: Paper[] = [
  {
    id: '1',
    title: 'Machine Learning Approaches for EMC Prediction in PCB Design',
    authors: ['Smith, J.', 'Johnson, A.', 'Williams, B.'],
    abstract: 'This paper presents novel machine learning techniques for predicting electromagnetic compatibility issues in printed circuit board designs...',
    url: 'https://ieeexplore.ieee.org/document/12345678',
    publishedDate: '2024-03-01',
    journalId: '1',
    topics: ['Machine Learning', 'EMC', 'PCB Design'],
  },
  {
    id: '2',
    title: 'Advanced Signal Integrity Analysis Using Deep Neural Networks',
    authors: ['Brown, C.', 'Davis, E.'],
    abstract: 'We propose a deep learning framework for analyzing signal integrity in high-speed digital circuits...',
    url: 'https://ieeexplore.ieee.org/document/12345679',
    publishedDate: '2024-03-03',
    journalId: '1',
    topics: ['Signal Integrity', 'Deep Learning'],
  },
  {
    id: '3',
    title: 'Neuromorphic Computing: Recent Advances and Future Directions',
    authors: ['Lee, K.', 'Park, S.', 'Kim, H.'],
    abstract: 'A comprehensive review of neuromorphic computing architectures and their applications...',
    url: 'https://www.nature.com/articles/s41928-024-01234-5',
    publishedDate: '2024-03-05',
    journalId: '2',
    topics: ['Neuromorphic Computing', 'Hardware'],
  },
];

const topicGroups: TopicGroup[] = [
  {
    topic: 'Machine Learning',
    paperCount: 2,
    papers: [mockPapers[0], mockPapers[1]],
  },
  {
    topic: 'EMC',
    paperCount: 1,
    papers: [mockPapers[0]],
  },
  {
    topic: 'Signal Integrity',
    paperCount: 1,
    papers: [mockPapers[1]],
  },
  {
    topic: 'Neuromorphic Computing',
    paperCount: 1,
    papers: [mockPapers[2]],
  },
];

export const mockDigest: Digest = {
  id: '1',
  generatedAt: '2024-03-08',
  startDate: '2024-03-01',
  endDate: '2024-03-08',
  papers: mockPapers,
  papersByTopic: {
    'Machine Learning': [mockPapers[0], mockPapers[1]],
    'EMC': [mockPapers[0]],
    'Signal Integrity': [mockPapers[1]],
    'Neuromorphic Computing': [mockPapers[2]],
  },
  topicGroups: topicGroups,
};

export const mockDigestHistory: Digest[] = [
  mockDigest,
  {
    id: '2',
    generatedAt: '2024-03-01',
    startDate: '2024-02-23',
    endDate: '2024-03-01',
    papers: [mockPapers[0]],
    papersByTopic: {
      'Machine Learning': [mockPapers[0]],
    },
    topicGroups: [
      {
        topic: 'Machine Learning',
        paperCount: 1,
        papers: [mockPapers[0]],
      },
    ],
  },
];

export const mockCredentials: Credential[] = [
  {
    id: '1',
    journalId: '1',
    journalName: 'IEEE Transactions on Electromagnetic Compatibility',
    username: 'user@example.com',
    addedAt: '2024-01-15',
    credentialType: 'username_password',
    maskedValue: '********',
  },
];
